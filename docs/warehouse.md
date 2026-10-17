# Data Warehouse & Dimensional Modeling
## Satellite Data Management and Geospatial Change Detection System
**Course:** DBMS Laboratory Course Project  
**Selected Track:** Track C — Data Warehouse and Analytics  

---

## 1. Grain of the Fact Table

> **The Grain of FACT_OBSERVATION:**  
> *One fact row represents one land-cover measurement for one satellite observation in one region on one date.*  
> (Exactly one row corresponding to each operational `observation_land_cover` measurement).

Enforcing the grain at the database level:
```sql
CONSTRAINT uq_fact_grain UNIQUE (region_key, date_key, sensor_key, land_cover_key)
```
This database-level unique constraint guarantees mathematical idempotency: re-running the ETL or inserting overlapping observation records will never inflate aggregated totals.

---

## 2. Star Schema Architecture

The dimensional model is structured in the `warehouse` schema and consists of:
- **1 Central Fact Table:** `fact_observation` (480 rows across 2021–2024 quarterly observations)
- **5 Conformed Dimension Tables:**
  1. `dim_satellite`: Natural key `satellite_id`, name, operator, status.
  2. `dim_sensor`: Natural key `sensor_id`, name, sensor_type, resolution.
  3. `dim_region`: Natural key `region_id`, name, region_type.
  4. `dim_date`: Integer surrogate key `YYYYMMDD` (1,826 pre-populated calendar dates).
  5. `dim_land_cover`: Natural key `land_cover_id`, name.

---

## 3. Core Architectural Decisions (Viva Defenses)

### 3.1 Why Surrogate Keys instead of Natural Keys?
1. **Source Independence:** The operational database may alter or purge primary keys during operational maintenance. The warehouse uses its own autonomous `SERIAL` surrogate keys (`*_key`) so the analytical warehouse history remains uncorrupted.
2. **No Operational Foreign Keys:** Dimension tables hold natural keys (`satellite_id`, etc.) purely as audit attributes, with **no direct foreign key back into `operational`**. The warehouse runs on its own refresh cycle.
3. **Performance:** Integer surrogate keys allow compact, dense indexes on the fact table foreign keys, speeding up multi-table hash joins.

### 3.2 Star Schema vs. Snowflake Schema
- **Snowflake Schema:** Normalizes dimensions into sub-dimensions (e.g. `dim_date` $\rightarrow$ `dim_month` $\rightarrow$ `dim_quarter` $\rightarrow$ `dim_year`). While theoretically in 3NF, querying requires multiple slow joins across sub-dimension tables.
- **Star Schema (Our Choice):** Flattens dimensions into single, denormalized tables. Slicing by `year`, `quarter`, or `month_name` requires joining only once to `dim_date`. For read-heavy analytical dashboards, Star Schema delivers superior execution speed.

### 3.3 Why `dim_date` is Pre-Populated
Rather than dynamically creating date records when observations arrive, `dim_date` is pre-populated with 1,826 days from `2021-01-01` to `2025-12-31` using PostgreSQL `GENERATE_SERIES`:
```sql
INSERT INTO dim_date (date_key, full_date, day, month, month_name, quarter, year)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER,
    d,
    EXTRACT(DAY FROM d)::INTEGER,
    EXTRACT(MONTH FROM d)::INTEGER,
    TO_CHAR(d, 'Month'),
    EXTRACT(QUARTER FROM d)::INTEGER,
    EXTRACT(YEAR FROM d)::INTEGER
FROM GENERATE_SERIES('2021-01-01'::DATE, '2025-12-31'::DATE, INTERVAL '1 day') AS d;
```
**Benefits:**
- Detects missing observation periods: Allows outer joins to identify quarters where a satellite missed an expected observation pass.
- Eliminates repeated expensive date extraction calculations during runtime queries.

---

## 4. OLAP Querying Techniques

### 4.1 Multi-Dimensional ROLLUP Aggregations
PostgreSQL `ROLLUP` produces hierarchical sub-totals and grand totals in a single database pass:
```sql
SELECT 
    COALESCE(dr.name, 'ALL REGIONS') AS region,
    COALESCE(dd.year::text, 'ALL YEARS') AS year,
    COALESCE(dlc.name, 'ALL CLASSES') AS land_cover,
    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_area_sq_km
FROM warehouse.fact_observation fo
JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
GROUP BY ROLLUP (dr.name, dd.year, dlc.name);
```

### 4.2 Window Functions (`LAG` & Rolling Moving Averages)
Calculates quarter-over-quarter and year-over-year deltas without self-joins:
```sql
-- Rolling 3-quarter window average
AVG(urban_sq_km) OVER (
    PARTITION BY region_name 
    ORDER BY year, quarter 
    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
) AS rolling_3q_avg_sq_km,

-- Year-over-year deforestation shift using LAG()
forest_sq_km - LAG(forest_sq_km) OVER (PARTITION BY region_name ORDER BY year) AS annual_loss_sq_km
```

### 4.3 Materialized Views
`warehouse.mvw_regional_quarterly_landcover` pre-computes regional quarterly summaries, reducing dashboard chart response times to under 5 milliseconds.
