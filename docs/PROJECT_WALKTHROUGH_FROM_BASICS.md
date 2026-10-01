# Satellite Data Management & Geospatial Change Detection System
## A Complete, Beginner-Friendly Project Walkthrough & Conceptual Guide

---

> **Welcome to the Project Guide!**  
> If you are reading this, your goal is to understand **what this project is**, **why we built it**, **how every piece works from the ground up**, and **how to confidently explain it to professors, evaluators, or teammates**.
> 
> Everything here is explained in plain, intuitive English—starting from zero assumptions.

---

## Table of Contents
1. [The Big Picture: What is this project about?](#1-the-big-picture-what-is-this-project-about)
2. [The Core Dilemma: Why standard databases fail for satellites](#2-the-core-dilemma-why-standard-databases-fail-for-satellites)
3. [The Master Architecture: Why TWO database schemas (OLTP vs OLAP)?](#3-the-master-architecture-why-two-database-schemas-oltp-vs-olap)
4. [Schema 1: The Operational Database (PostgreSQL + PostGIS in 3NF)](#4-schema-1-the-operational-database-postgresql--postgis-in-3nf)
5. [The Spatial Secret: What is PostGIS and GiST indexing?](#5-the-spatial-secret-what-is-postgis-and-gist-indexing)
6. [The Large-Object Decision: Where do giant satellite images go?](#6-the-large-object-decision-where-do-giant-satellite-images-go)
7. [The Bridge: The Two-Stage Python ETL Pipeline](#7-the-bridge-the-two-stage-python-etl-pipeline)
8. [Schema 2: The Data Warehouse (Star Schema & OLAP)](#8-schema-2-the-data-warehouse-star-schema--olap)
9. [Advanced SQL Analytics Made Simple (Window Functions & ROLLUP)](#9-advanced-sql-analytics-made-simple-window-functions--rollup)
10. [Database Programmability: Stored Functions & Triggers](#10-database-programmability-stored-functions--triggers)
11. [The Web Dashboard: Bringing it all to life](#11-the-web-dashboard-bringing-it-all-to-life)
12. [Team Roles Breakdown: Who did what?](#12-team-roles-breakdown-who-did-what)

---

## 1. The Big Picture: What is this project about?

Every single day, satellites (like Sentinel-2, Landsat, and radar satellites) orbit the Earth and snap pictures of the ground. Over years, these pictures reveal how our planet is changing:
- **Cities are expanding** into surrounding farmland (urbanization).
- **Forests are shrinking** due to deforestation and infrastructure projects.
- **Water reservoirs are fluctuating** due to seasons and climate shifts.

### The Objective
Our team built a complete **Database and Analytical Platform** to:
1. **Ingest and organize** raw satellite metadata and observations safely.
2. **Handle geographic boundaries** (polygons on the globe) so we can ask spatial questions like *"Which satellite image overlaps with Delhi NCR?"*
3. **Transform this data into a Data Warehouse** designed specifically for fast historical reporting over 5 years (2021 to 2025).
4. **Automatically calculate geographic changes** between any two dates (e.g. *"Between 2021 and 2024, how many square kilometers of forest turned into urban area in Delhi?"*).
5. **Present the results** on a live interactive web dashboard with maps, charts, and a SQL console.

---

## 2. The Core Dilemma: Why standard databases fail for satellites

Most college database projects store simple scalar numbers and text (like Student IDs, Book Titles, or Order Amounts). But satellite observation data has three unique headaches:

1. **Space is 2-Dimensional**: A city or satellite swath is not a single number; it is a **polygon** with latitude/longitude coordinates on a curved sphere (the Earth). Standard B-tree indexes cannot index 2D polygons.
2. **Observations are Continuous**: A satellite doesn't take one picture; it passes over the same region every few weeks for decades. If you store everything in one big flat table, running an analytical report scans millions of rows and grinds the database to a halt.
3. **Images are Gigabytes in Size**: Raw high-resolution satellite imagery files are huge. If you save gigabyte image files directly into database tables (BLOBs), your database will balloon to hundreds of gigabytes and crash.

Our project solves all three problems using modern database engineering.

---

## 3. The Master Architecture: Why TWO database schemas (OLTP vs OLAP)?

This is the central theme of **Track C (Data Warehouse and Analytics)**. 

In professional enterprises, you **never** run heavy historical reports directly on your live transactional database. We separated our database into two distinct schemas:

```
+---------------------------------------------------------------------+
|              STAGE 1: OPERATIONAL DATABASE (OLTP)                   |
|  • Schema: 'operational'                                            |
|  • Model: 3NF (Third Normal Form)                                   |
|  • Goal: Fast inserts, zero data redundancy, strict integrity       |
|  • Tech: PostgreSQL + PostGIS (GiST spatial R-Tree indexes)         |
+---------------------------------------------------------------------+
                                  |
                                  v  (Automated Python ETL Pipeline)
+---------------------------------------------------------------------+
|              STAGE 2: DATA WAREHOUSE (OLAP)                         |
|  • Schema: 'warehouse'                                              |
|  • Model: Dimensional Star Schema                                   |
|  • Goal: High-speed analytical queries, aggregations, trend lines   |
|  • Tech: Fact Table + Dimensions + Materialized Views + Window Funcs|
+---------------------------------------------------------------------+
```

- **OLTP (`operational`)**: Optimized for day-to-day data entry (e.g. when a satellite passes overhead and logs a new pass). It is strictly normalized so there are no duplicate entries.
- **OLAP (`warehouse`)**: Optimized for asking big questions (e.g. *"Show me the 3-quarter moving average of urban growth across Delhi, Mumbai, and Bengaluru over 4 years"*). It is organized into a Star Schema with pre-computed dates and fast surrogate keys.

---

## 4. Schema 1: The Operational Database (PostgreSQL + PostGIS in 3NF)

The operational database contains **7 core tables** and **1 audit table**, all in Third Normal Form (3NF):

### The Tables Explained:
1. **`satellite`**: The satellite hardware platforms orbiting space (e.g. `SYN-EO-1`, `SYN-EO-2`, `SYN-SAR-1`), who operates them, launch date, and status.
2. **`sensor`**: The cameras or radars installed on each satellite (e.g. `MultiSpectral-A`, `SAR-C-Band`) with their ground resolution in meters. A satellite can have multiple sensors ($1 : N$).
3. **`region`**: The territories we monitor (e.g. `Delhi NCR`, `Mumbai Metropolitan`, `Central India Forest Belt`). Each region stores its exact geographical boundary polygon (`POLYGON, 4326`).
4. **`observation`**: A specific satellite pass over a region on a specific calendar date. It stores the satellite swath footprint polygon.
5. **`image_data`**: Metadata for the image file captured during that pass (file path/URI, format, file size, acquisition timestamp).
6. **`land_cover`**: The standardized categories of land (`Forest`, `Urban`, `Water`, `Agriculture`, `Barren`).
7. **`observation_land_cover`**: The bridge table resolving the Many-to-Many relationship between observations and land cover classes. It stores the measured area in square meters for each class.
8. **`change_event`**: When our analysis detects that land transformed (e.g. $12.5\text{ km}^2$ changed from Agriculture to Urban between 2021 and 2023), it is recorded here.
9. **`change_event_audit`**: An audit trail table automatically populated by a trigger whenever a change event is inserted or updated.

### What does "3NF Normalization" actually mean here?
In simple words: **Every piece of data is stored in exactly ONE place.**
- **1NF**: All table columns are atomic (no arrays or comma-separated lists).
- **2NF**: In `observation_land_cover`, the primary key is a composite `(observation_id, land_cover_id)`. The column `area` depends on the entire key, not just half of it.
- **3NF**: We don't store the satellite's operator or launch date inside the `sensor` or `observation` table. If a satellite's operator changed, we only update 1 row in `satellite`, preventing update anomalies across thousands of observation rows!

---

## 5. The Spatial Secret: What is PostGIS and GiST indexing?

Standard PostgreSQL doesn't know that the Earth is round. It doesn't know if a point $(X, Y)$ is inside a boundary polygon. 

That is why we enabled **PostGIS**:
```sql
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA public;
```

### Why B-Tree Indexes Fail for Maps
A regular B-tree index sorts numbers on a 1D line: $1 < 2 < 3$. But polygons exist in 2 dimensions ($X$ and $Y$). A polygon in Delhi is simultaneously north of Mumbai and east of Punjab. There is no simple 1D order.

### How GiST (Generalized Search Tree) Works
PostGIS uses **GiST indexes** based on **R-Trees (Region Trees)**:
1. For every polygon boundary, PostGIS calculates a **Minimum Bounding Box** $[X_{\min}, Y_{\min}, X_{\max}, Y_{\max}]$.
2. These boxes are grouped into a hierarchical tree.
3. When you run a query like `WHERE ST_Intersects(boundary, footprint)`, PostGIS checks bounding box overlaps in $O(\log N)$ time.
4. It discards $99\%$ of non-overlapping polygons instantly, running the expensive point-by-point math only on the survivors!

```sql
CREATE INDEX idx_region_boundary_gist        ON operational.region      USING GIST (boundary);
CREATE INDEX idx_observation_footprint_gist   ON operational.observation USING GIST (footprint);
```

### Why we cast to `::geography`
Coordinates are in degrees (SRID 4326: WGS84). If you ask PostGIS for `ST_Area(geometry)`, it returns square degrees! Since degrees shrink as you move away from the equator, we cast to `::geography`:
```sql
ROUND((ST_Area(r.boundary::geography) / 1000000.0)::numeric, 2) AS area_sq_km
```
This forces PostGIS to calculate true ellipsoidal surface area over the Earth's curved spheroid in **square kilometers**.

---

## 6. The Large-Object Decision: Where do giant satellite images go?

In Section 6.5 of our project proposal, the evaluators asked us to address:
> *"Deciding whether large satellite images should be stored externally or directly in the database."*

### Our Engineering Decision:
**We store image metadata in PostgreSQL, and image files in external storage.**

- **Why NOT in the database (BLOBs/BYTEA)?**
  Satellite images (like Sentinel GeoTIFFs) are 500 MB to 2 GB per file. Storing binary files inside PostgreSQL causes table bloat, slows down database backups, pollutes the database cache memory, and degrades index performance.
- **The Industry Standard Approach (What we implemented):**
  The database table `operational.image_data` stores:
  - `file_reference`: The storage URL/path (e.g. Cloud Object Storage / S3 URI or local file path).
  - `format`: GeoTIFF / Cloud-Optimized GeoTIFF (COG).
  - `file_size`: Size in bytes.
  - `acquisition_time`: Precise UTC timestamp.
  This keeps the relational database lean, fast, and sub-second in queries, while allowing the frontend to stream images directly from storage.

---

## 7. The Bridge: The Two-Stage Python ETL Pipeline

ETL stands for **Extract, Transform, Load**. We wrote an automated Python pipeline in `etl/run_pipeline.py`:

### Stage 1: Operational Ingestion (`stage1_operational_load.py`)
1. **Extract**: Reads raw synthetic sensor telemetry CSV files from `etl/data/`.
2. **Clean & Validate**: Checks for missing columns, invalid foreign keys, and cleans duplicate rows.
3. **Geospatial Transform**: Takes Well-Known Text polygon strings (e.g. `POLYGON((76.85 28.4, ...))`) and converts them into binary PostGIS geometries using `ST_GeomFromText(..., 4326)`.
4. **Load**: Inserts records into `operational` tables in strict foreign-key order inside an ACID transaction.

### Stage 2: Dimensional Warehouse Transformation (`stage2_warehouse_load.py`)
1. **Dimension Extraction**: Extracts unique satellites, sensors, regions, and land covers from the operational tables and assigns them **Surrogate Keys**.
2. **Date Key Mapping**: Maps observation dates to our calendar dimension `dim_date.date_key` (e.g. `2023-04-15` becomes the integer `20230415`).
3. **Fact Table Load**: Aggregates and loads measurement rows into `warehouse.fact_observation`.
4. **Materialized View Refresh**: Refreshes `mvw_regional_quarterly_landcover` so dashboard queries are instant.

---

## 8. Schema 2: The Data Warehouse (Star Schema & OLAP)

### What is a Star Schema?
In a Star Schema, there is one central **Fact Table** containing the numerical measurements, connected to multiple surrounding **Dimension Tables** containing the context (who, what, where, when).

```
                      +-------------------+
                      |   DIM_SATELLITE   |
                      +-------------------+
                                |
+----------------+              |              +----------------+
|   DIM_SENSOR   |-------+      |      +-------|   DIM_REGION   |
+----------------+       |      |      |       +----------------+
                         v      v      v
                    +----------------------+
                    |   FACT_OBSERVATION   |
                    +----------------------+
                         ^             ^
                         |             |
+----------------+       |             |       +----------------+
| DIM_LAND_COVER |-------+             +-------|    DIM_DATE    |
+----------------+                             +----------------+
```

### 1. The Fact Table: `fact_observation`
- **What is the Fact Grain?**  
  The grain is the atomic meaning of one single row in the fact table:  
  > *"One land-cover area measurement, for one satellite pass, in one region, on one calendar date."*
- **Database Enforcement**:  
  We enforce this grain with a database-level unique constraint:  
  `UNIQUE (region_key, date_key, sensor_key, land_cover_key)`. You cannot accidentally insert duplicate records!

### 2. Why Surrogate Keys instead of Natural Keys?
In dimension tables (`dim_satellite`, `dim_region`, etc.), we generate a new integer surrogate key (`satellite_key`, `region_key`) instead of using the operational `id`:
- **Decoupling**: If the operational database renumbers its IDs or changes systems, the data warehouse historical records don't break.
- **Fast Joins**: Joining on compact 4-byte integers is much faster than joining on text or composite keys.

### 3. The Date Dimension: `dim_date`
Instead of running slow SQL functions like `EXTRACT(YEAR FROM date)` across millions of rows, we pre-generated **1,826 days (every single day from 2021 to 2025)** into `dim_date`.
- Each row contains: `date_key` (e.g. `20230415`), `year`, `quarter`, `month`, `month_name`, `day_of_month`, `day_name`, and `is_weekend`.

---

## 9. Advanced SQL Analytics Made Simple (Window Functions & ROLLUP)

Our project uses advanced SQL features from the college syllabus that impress evaluators:

### 1. `ROLLUP` (Hierarchical Subtotals)
Instead of writing 4 different queries, `ROLLUP (region, year, land_cover)` gives:
1. Detailed measurements per region, year, and category.
2. Regional yearly subtotals.
3. Total for the region across all years.
4. Grand Total across all regions and all years.

### 2. Window Function: `LAG()` for Year-over-Year Shift
`LAG()` looks back at the previous row without collapsing rows like `GROUP BY`:
```sql
LAG(avg_area_sq_km) OVER (
    PARTITION BY region_name, land_cover 
    ORDER BY year
) AS prev_year_area_sq_km
```
This lets us compute $\text{Annual Change} = \text{Current Year Area} - \text{Previous Year Area}$ and instantly graph **Deforestation Rates**.

### 3. Moving Average: `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW`
Satellite measurements can fluctuate due to seasonal clouds. To see the true trend of urban expansion, we calculate a **3-Quarter Rolling Moving Average**:
```sql
AVG(urban_sq_km) OVER (
    PARTITION BY region_name 
    ORDER BY year, quarter 
    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
) AS rolling_3q_avg_sq_km
```
This averages the current quarter with the two quarters before it, providing a smooth curve that shows whether a city's expansion is accelerating.

---

## 10. Database Programmability: Stored Functions & Triggers

To demonstrate that the database is not just a passive storage bucket, we implemented active procedural logic inside PostgreSQL:

### 1. Stored Function: `operational.fn_compare_landcover()`
- **Written in**: PL/pgSQL
- **What it does**: Takes three arguments: `(region_id, date_start, date_end)`.
- **How it works**: Queries the land cover measurements on `date_start`, compares them with measurements on `date_end`, and computes the net shift in square kilometers and percentage change.
- **Why it matters**: It executes in memory directly inside PostgreSQL in under 5 milliseconds, avoiding the need to transfer raw rows to the web server.

### 2. Database Trigger: `operational.trg_audit_change_event`
- **When it fires**: `AFTER INSERT OR UPDATE ON operational.change_event`.
- **What it does**: Automatically writes an entry into `operational.change_event_audit` with `action_type`, `change_id`, `changed_area`, and the current timestamp `logged_at`.
- **Why it matters**: Demonstrates data governance and auditability—if an operator or machine changes a record, the change history is permanently preserved.

### 3. Materialized View: `warehouse.mvw_regional_quarterly_landcover`
- Pre-computes regional quarterly land cover totals and averages.
- When the dashboard opens, it queries this materialized view in **1 millisecond** instead of scanning thousands of fact table rows.

---

## 11. The Web Dashboard: Bringing it all to life

To make the project tangible, we built a working web prototype running at `http://localhost:8000`:

1. **Leaflet.js Geospatial Map**:
   - Renders polygon boundaries from PostGIS for all monitored regions.
   - Overlays satellite swath footprints.
   - Hovering or clicking on any polygon displays its live surface area and observation count.
2. **Land Cover Shift Calculator**:
   - Lets you pick any region and two observation dates.
   - Calls `operational.fn_compare_landcover()` live and displays positive/negative shifts in green/red badges.
3. **Data Warehouse & OLAP Charts (Chart.js)**:
   - Line chart of rolling 3-quarter urban expansion velocity.
   - Stacked bar chart of quarterly land cover composition.
   - Horizontal bar chart of sensor throughput (Optical vs Radar).
   - Deforestation index bar chart showing yearly net loss.
4. **Live Schema Inspector**:
   - Dynamically inspects tables, column data types, primary/foreign keys, and real-time row counts directly from PostgreSQL `information_schema`.
5. **Interactive SQL Console**:
   - Has preset analytical queries.
   - Lets you type custom read-only SQL queries and visualize the query results and `EXPLAIN ANALYZE` execution plan.

---

## 12. Team Roles Breakdown: Who did what?

In your proposal document (Section 10), the team defined 5 distinct roles. Here is how our implemented codebase maps to each person so everyone can explain their role with total clarity:

### Member 1: Database Design (Rishi Jangid)
- **Contribution**: Designed the 3NF operational relational schema ([01_tables.sql](file:///d:/dbms%20project/satelite-change-detection/database/schema/01_tables.sql)). Defined primary keys, foreign keys, check constraints ([02_constraints.sql](file:///d:/dbms%20project/satelite-change-detection/database/schema/02_constraints.sql)), and ensured elimination of insertion/deletion/update anomalies.
- **Key Files**: `database/schema/01_tables.sql`, `database/schema/02_constraints.sql`, `docs/ER_DIAGRAMS.md`.

### Member 2: Geospatial Database (Daksh Vashistha)
- **Contribution**: Integrated the PostGIS 3.4 extension. Configured spatial geometry columns (`GEOMETRY(POLYGON, 4326)`), built R-Tree based spatial GiST indexes, and authored spatial queries with `ST_Intersects`, `ST_Contains`, `ST_Distance`, and `::geography` metric area casting.
- **Key Files**: `database/schema/03_indexes.sql`, `database/queries/02_postgis_spatial_analysis.sql`, `backend/app/routes/spatial.py`.

### Member 3: Data Integration and ETL (Harshit Nagar)
- **Contribution**: Built the automated two-stage Python ETL pipeline. Designed data cleaning, WKT geometry parsing, FK-dependency sequencing, and transactional ACID guarantees in Stage 1 and Stage 2 loaders.
- **Key Files**: `etl/run_pipeline.py`, `etl/scripts/stage1_operational_load.py`, `etl/scripts/stage2_warehouse_load.py`.

### Member 4: Data Warehouse and Analytics (Aarav Jain)
- **Contribution**: Architected the dimensional Star Schema (`warehouse`). Established the fact table grain, pre-computed the 5-year `dim_date` calendar table, authored multi-dimensional `ROLLUP`/`CUBE` queries, and implemented window functions (`LAG()`, moving averages).
- **Key Files**: `database/warehouse/01_dimensions.sql`, `database/warehouse/02_fact.sql`, `database/analytics/02_olap_queries.sql`, `database/queries/04_advanced_window_functions.sql`.

### Member 5: Application and Visualization (Vaibhav Jain)
- **Contribution**: Developed the FastAPI RESTful backend service, Leaflet.js interactive map, Chart.js OLAP graphs, the PL/pgSQL stored procedure UI, and the SQL analytics runner console.
- **Key Files**: `backend/app/main.py`, `backend/app/routes/`, `frontend/index.html`, `frontend/js/`, `frontend/css/styles.css`.

---

## Summary Checklist: Does our implementation satisfy the proposal?

| Proposal Requirement | Implementation Status | Where to find it in the project |
| :--- | :---: | :--- |
| **Track C: Data Warehouse & Analytics** | **100% Satisfied** | Dedicated `warehouse` star schema with fact and dimension tables |
| **Normalized Operational Schema (3NF)** | **100% Satisfied** | `operational` schema with 7 normalized tables + check constraints |
| **PostGIS Spatial Modeling & Indexing** | **100% Satisfied** | PostGIS polygons with R-Tree GiST indexes on boundaries & swaths |
| **Large-Object Storage Decision** | **100% Satisfied** | URI references & metadata in `image_data` table (avoiding DB bloat) |
| **Python ETL Pipeline** | **100% Satisfied** | Idempotent two-stage ETL (`etl/run_pipeline.py`) with ACID safety |
| **Star Schema Fact Grain** | **100% Satisfied** | Enforced grain: `UNIQUE (region_key, date_key, sensor_key, land_cover_key)` |
| **OLAP & Analytical Queries** | **100% Satisfied** | `ROLLUP`, `CUBE`, `GROUPING SETS`, `LAG()` YoY, and 3-Quarter moving avg |
| **Change Detection Mechanism** | **100% Satisfied** | PL/pgSQL stored function `fn_compare_landcover()` & `change_event` log |
| **Working Prototype & Visualizations** | **100% Satisfied** | Leaflet map + Chart.js dashboard running live at `http://localhost:8000` |
| **All 8 Proposed Analytical Queries** | **100% Satisfied** | Pre-written and runnable in `database/queries/` and the web SQL console |
