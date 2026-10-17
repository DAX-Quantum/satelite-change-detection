# System Architecture & Technical Design
## Satellite Data Management and Geospatial Change Detection System
**Track C — Data Warehouse and Analytics**

---

## 1. High-Level Architectural Overview

The system employs a **two-tier hybrid architecture** hosted inside a single PostgreSQL 16 + PostGIS 3.4 database cluster, logically partitioned into two distinct schemas:

1. **`operational` (OLTP Schema):** Normalized to **Third Normal Form (3NF)**. Designed for ACID compliance, transactional ingest, spatial topological integrity, and sensor telemetry tracking without redundant attributes.
2. **`warehouse` (OLAP Schema):** Modeled as a **Star Schema**. Optimized for fast multi-dimensional aggregations, analytical slicing/dicing, rollups, window functions, and historical time-series reporting.

```
                    ┌──────────────────────────────────┐
                    │     Synthetic CSV Data Sources    │
                    │   satellites, sensors, regions,   │
                    │   observations, land_cover, etc. │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │    Python ETL Stage 1        │
                       │  - Validate columns & PKs    │
                       │  - Transform WKT to PostGIS  │
                       │  - Bulk load via transactions│
                       └──────────────┬───────────────┘
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │       PostgreSQL 16 + PostGIS 3.4 Container      │
             │                                                  │
             │  ┌────────────────────┐   ┌───────────────────┐  │
             │  │ operational schema │   │ warehouse schema  │  │
             │  │ - 3NF Normalized   │   │ - Star Schema     │  │
             │  │ - PostGIS GiST     │──>│ - 5 Dimensions    │  │
             │  │ - Strict PKs/FKs   │   │ - FACT_OBSERVATION│  │
             │  │ - Triggers & Views │   │ - Materialized VWs│  │
             │  └────────────────────┘   └───────────────────┘  │
             └────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │     FastAPI / Node API       │
                       │  - Parameterized SQL         │
                       │  - GeoJSON spatial delivery  │
                       │  - Stored procedure triggers │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │  Vibrant Web Dashboard (UI)  │
                       │  - Leaflet PostGIS map       │
                       │  - Chart.js OLAP graphs      │
                       │  - Change detection matrix   │
                       │  - SQL viva execution lab    │
                       └──────────────────────────────┘
```

---

## 2. The Two Schemas: OLTP vs. OLAP

| Architectural Dimension | Operational (`operational`) | Data Warehouse (`warehouse`) |
| :--- | :--- | :--- |
| **Primary Workload** | OLTP (Online Transaction Processing) | OLAP (Online Analytical Processing) |
| **Design Paradigm** | 3NF (Third Normal Form) | Dimensional Modeling (Star Schema) |
| **Optimization Focus** | Fast writes, data integrity, 0 redundancy | Read-heavy queries, fast aggregation, history |
| **Key Strategy** | Natural keys & Composite PKs | Independent Surrogate Keys (`*_key SERIAL`) |
| **Spatial Handling** | Full native geometries (`POLYGON`, GiST) | Metric aggregates (`area`, counts, period) |
| **Grain** | Single observation or sensor entity | *One land-cover measurement per observation* |
| **Denormalization** | Completely avoided | Intentionally applied (e.g. `dim_date`) |

---

## 3. Two-Stage ETL Pipeline Design

### Stage 1: Operational Ingestion (`stage1_operational_load.py`)
1. **Extraction & Validation:** Reads synthetic CSV files from `etl/data/`. Checks for required columns and drops invalid rows.
2. **Deduplication:** Deduplicates rows based on the table's true primary key. For associative table `observation_land_cover`, deduplication is strictly evaluated on `(observation_id, land_cover_id)`.
3. **Spatial Conversion:** Converts Well-Known Text (WKT) geometries into PostGIS native geometries using `ST_GeomFromText(%s, 4326)`.
4. **Transactional Idempotency:** Executes `TRUNCATE ... RESTART IDENTITY CASCADE` followed by bulk insertion with `psycopg2.extras.execute_values` inside an atomic transaction.

### Stage 2: Warehouse Dimensional Load (`stage2_warehouse_load.py`)
1. **Dimension Extraction:** Queries operational tables to populate or update dimensions (`dim_satellite`, `dim_sensor`, `dim_region`, `dim_land_cover`).
2. **Surrogate Key Generation:** Assigns independent integer surrogate keys. Natural IDs are retained as non-FK attributes for audit traceability.
3. **Fact Table Assembly:** Joins `operational.observation_land_cover` with `observation` and dimension lookup maps.
4. **Grain Constraint Enforcement:** Inserts 480 fact rows into `warehouse.fact_observation`. Database constraint `uq_fact_grain UNIQUE (region_key, date_key, sensor_key, land_cover_key)` guarantees that accidental ETL re-runs will never create duplicate aggregations.

---

## 4. PostGIS Spatial Architecture
- **Coordinate Reference System:** EPSG:4326 (WGS84 ellipsoidal coordinates: longitude, latitude in degrees).
- **Metric Calculations:** To compute accurate metric areas without distortion from latitude degree convergence, geometries are cast to `geography` type:
  ```sql
  ROUND((ST_Area(boundary::geography) / 1000000.0)::numeric, 2) AS area_sq_km
  ```
- **Spatial Indexing:** GiST indexes (`CREATE INDEX idx_region_boundary ON region USING GIST (boundary);`) construct an R-tree over geometry bounding boxes. Queries like `ST_Intersects` use the bounding box to prune non-candidate polygons in $O(\log N)$ time before executing exact vertex calculations.

---

## 5. Security & Student Production Considerations
- **Environment Isolation:** Secrets (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`) loaded through `.env`.
- **Default Port 5433:** Binds to host port `5433` (`"${POSTGRES_PORT:-5433}:5432"`) to eliminate collisions with any existing local PostgreSQL service running on standard port `5432`.
- **SQL Injection Prevention:** Every query executed in the backend uses parameterized placeholders (`%s`). Direct string concatenation in SQL is strictly prohibited.
