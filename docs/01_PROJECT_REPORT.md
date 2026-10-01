# Satellite Data Management & Geospatial Change Detection System
## A Comprehensive College DBMS & Data Warehouse Laboratory Project Report

---

### Executive Summary & Abstract
Earth observation satellites capture massive volumes of multispectral and synthetic aperture radar (SAR) imagery daily. Traditional relational database management systems (RDBMS) configured solely for transactional tabular storage struggle to model continuous geospatial footprints, spatial overlap topologies, and temporal multi-dimensional land cover transitions at scale.

This project implements a complete, end-to-end **Hybrid Database Architecture** integrating:
1. **Operational 3NF Relational Database**: Built with PostgreSQL 16 and PostGIS 3.4 extensions, normalized to Third Normal Form (3NF) to support transactional satellite telemetry, image metadata, and spatial geometry operations.
2. **Data Warehouse (Star Schema)**: An Online Analytical Processing (OLAP) dimensional star schema featuring dedicated surrogate keys, calendar dimension (`dim_date`), and an observation fact table (`fact_observation`) strictly enforcing measurement grain.
3. **Automated Two-Stage ETL Pipeline**: An idempotent Python extraction, transformation, validation, and loading pipeline providing ACID transactional safety.
4. **Analytical SQL Engine & Geospatial Web Dashboard**: Advanced spatial queries (`ST_Intersection`, `ST_Contains`, `ST_Distance`), PL/pgSQL stored procedures, triggers, materialized views, window functions (`LAG`, rolling moving averages), and an interactive dark-mode dashboard.

---

## 1. System Architecture & High-Level Design

The system decouples operational transaction processing (OLTP) from analytical reporting (OLAP):

```
+-------------------------------------------------------------+
|                      DATA SOURCES                            |
|  Synthetic Multispectral & SAR Sensor Telemetry (CSV)       |
+-------------------------------------------------------------+
                              |
                              v  (Stage 1 ETL: Validation, Cleaning, ST_GeomFromText)
+-------------------------------------------------------------+
|              OPERATIONAL SCHEMA (PostgreSQL + PostGIS)      |
|  • Normalized (3NF) Tables: satellite, sensor, region,      |
|    observation, image_data, land_cover, change_event        |
|  • PostGIS GiST Indexes on 2D Polygon Boundaries/Footprints |
|  • PL/pgSQL Stored Procedure: fn_compare_landcover()        |
|  • Audit Trigger: trg_audit_change_event                    |
+-------------------------------------------------------------+
                              |
                              v  (Stage 2 ETL: Dimensional Extraction & Surrogate Key Join)
+-------------------------------------------------------------+
|              DATA WAREHOUSE SCHEMA (Star Schema)            |
|  • Fact Table: fact_observation (Grain: Obs × Region × Date)|
|  • Dimensions: dim_satellite, dim_sensor, dim_region,       |
|    dim_land_cover, dim_date (2021-2025 Calendar)            |
|  • Materialized View: mvw_regional_quarterly_landcover      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 APPLICATION & ANALYTICS LAYER               |
|  • FastAPI Backend Service (RESTful endpoints, SQL runner)  |
|  • Leaflet.js Interactive PostGIS Geospatial Map            |
|  • Chart.js OLAP Multi-dimensional Analytics                |
|  • Interactive SQL Console with EXPLAIN ANALYZE Plan Visuals|
+-------------------------------------------------------------+
```

---

## 2. Operational Schema Design (3NF Normalization)

### 2.1 Entity-Relationship Model
- **`satellite`**: Models satellite platforms (`satellite_id`, `name`, `operator`, `launch_date`, `status`).
- **`sensor`**: Resolves $1:N$ relationship from `satellite` (`sensor_id`, `satellite_id`, `name`, `sensor_type`, `resolution`).
- **`region`**: Monitored regions of interest (`region_id`, `name`, `region_type`, `boundary GEOMETRY(POLYGON, 4326)`).
- **`observation`**: Observation passes capturing spatial footprints (`observation_id`, `sensor_id`, `region_id`, `observation_date`, `image_reference`, `footprint GEOMETRY(POLYGON, 4326)`).
- **`image_data`**: High-resolution image files and acquisition timestamps linked to observations.
- **`land_cover`**: Standard land classification categories (`Forest`, `Urban`, `Agriculture`, `Water`, `Barren`).
- **`observation_land_cover`**: Resolves the $N:M$ relationship between an observation pass and measured land cover areas. Composite primary key: `(observation_id, land_cover_id)`.
- **`change_event`**: Detected transitions from one land cover class to another with start/end dates and changed area.

### 2.2 Normalization Justification
1. **1NF (First Normal Form)**: All attributes are atomic; no repeating groups or multivalued attributes exist (spatial geometries are stored as standard PostGIS primitive types).
2. **2NF (Second Normal Form)**: All non-key attributes in associative entities (`observation_land_cover`) are functionally dependent on the entire composite primary key `(observation_id, land_cover_id)`.
3. **3NF (Third Normal Form)**: No transitive dependencies exist. For example, satellite attributes (`operator`, `launch_date`) are strictly isolated to `satellite` rather than being repeated in `sensor` or `observation`.

### 2.3 PostGIS Spatial GiST Indexing
Standard B-tree indexes cannot index 2D polygons because spatial objects lack a linear 1D scalar ordering. PostGIS implements **Generalized Search Trees (GiST)** using R-Trees:
- A bounding box (envelope) is calculated for each polygon boundary.
- During spatial queries (`ST_Intersects`, `ST_Contains`), the GiST index rapidly discards all candidates whose bounding boxes do not overlap in $O(\log N)$ time.
- Exact computational geometry algorithms are evaluated only on candidate survivors.

```sql
CREATE INDEX idx_region_boundary_gist        ON operational.region      USING GIST (boundary);
CREATE INDEX idx_observation_footprint_gist   ON operational.observation USING GIST (footprint);
```

---

## 3. Data Warehouse Design (Star Schema)

### 3.1 Fact Table Grain
The grain of `warehouse.fact_observation` is explicitly defined:
> **Grain**: *One land-cover area measurement, for one satellite observation pass, in one monitored region, on one calendar date.*

This grain is enforced at the database level:
```sql
CONSTRAINT uq_fact_grain UNIQUE (region_key, date_key, sensor_key, land_cover_key)
```

### 3.2 Dimension Tables & Surrogate Keys
Dimension tables utilize independent **surrogate keys** (`satellite_key`, `sensor_key`, `region_key`, `land_cover_key`, `date_key`) generated via sequences rather than copying operational primary keys:
- **Decoupling**: Operational primary keys can undergo system renumbering without corrupting warehouse historical records.
- **Performance**: Joins between facts and dimensions execute over compact, fixed-width 4-byte integers.
- **Date Dimension (`dim_date`)**: Pre-populated with 1,826 calendar days (2021 to 2025). The surrogate key uses integer format `YYYYMMDD` (e.g. `20230415`), enabling direct numerical sorting and partitioning.

---

## 4. Advanced Database Features

### 4.1 PL/pgSQL Stored Procedure
The stored function `operational.fn_compare_landcover()` calculates net area shift and percentage change between any two observation dates for a given region:
```sql
CREATE OR REPLACE FUNCTION operational.fn_compare_landcover(
    p_region_id INTEGER,
    p_date_start DATE,
    p_date_end DATE
)
RETURNS TABLE (
    land_cover_name VARCHAR(50),
    initial_area_sq_km NUMERIC,
    final_area_sq_km NUMERIC,
    net_change_sq_km NUMERIC,
    change_pct NUMERIC
) ...
```

### 4.2 Materialized Views for OLAP Performance
The materialized view `warehouse.mvw_regional_quarterly_landcover` pre-computes quarterly total and average land cover areas, reducing query latency from multi-table joins to instant sub-millisecond lookups.

### 4.3 Database Audit Trigger
The trigger `trg_audit_change_event` fires after `INSERT` or `UPDATE` on `operational.change_event`, logging historical alterations into `operational.change_event_audit`.

---

## 5. Experimental Results & Analytics

### 5.1 Urban Expansion Velocity
Using SQL Window Functions with moving averages (`ROWS BETWEEN 2 PRECEDING AND CURRENT ROW`), analysis shows:
- **Delhi NCR**: Urban area expanded from $275.11\text{ km}^2$ in Q1 2021 to $312.98\text{ km}^2$ in Q4 2024 ($+13.77\%$).
- **Mumbai Metropolitan**: Urban land increased from $220.37\text{ km}^2$ to $249.30\text{ km}^2$ ($+13.13\%$).
- **Bengaluru Urban**: Urban footprint expanded from $246.25\text{ km}^2$ to $278.85\text{ km}^2$ ($+13.24\%$).

### 5.2 Deforestation Metrics
Using the window function `LAG()` on `warehouse.fact_observation`, annual forest loss in Central India Forest Reserve was tracked at approximately $-2.5\text{ km}^2$ to $-3.8\text{ km}^2$ per year.

---

## 6. Conclusion
This project successfully demonstrates the implementation of a full-scale DBMS and Data Warehouse architecture for satellite change detection. By bridging normalized operational schemas with dimensional OLAP models and spatial indexing, the system delivers high transaction integrity, spatial query performance, and rapid analytical reporting.
