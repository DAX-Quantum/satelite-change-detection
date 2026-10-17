# Satellite Data Management & Geospatial Change Detection System
### A Hybrid Relational (3NF + PostGIS) & Dimensional Data Warehouse (Star Schema) Platform

![Database](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Spatial](https://img.shields.io/badge/PostGIS-3.4_Spatial_GiST-emerald)
![Architecture](https://img.shields.io/badge/Architecture-3NF_OLTP_%2B_Star_Schema_OLAP-purple)
![Backend](https://img.shields.io/badge/Backend-FastAPI_Python-teal?logo=fastapi)
![Frontend](https://img.shields.io/badge/Frontend-Leaflet.js_%2B_Chart.js-orange)
![Container](https://img.shields.io/badge/Docker-compose_enabled-2496ED?logo=docker)

---

## Executive Summary & System Overview

Earth observation satellites capture massive volumes of multispectral and synthetic aperture radar (SAR) telemetry daily. Relational database management systems (RDBMS) configured solely for transactional 1D scalar data struggle to index continuous 2D spatial footprints, evaluate geometric overlaps, and compute historical multi-year land cover transitions at scale.

This project delivers a complete, production-grade **Hybrid Database Architecture** integrating:
1. **Operational 3NF Relational Database**: Built with PostgreSQL 16 and PostGIS 3.4 extensions, normalized to Third Normal Form (3NF) to support transactional satellite telemetry, image metadata, and spatial geometry operations without update/delete anomalies.
2. **Data Warehouse (Star Schema)**: An Online Analytical Processing (OLAP) dimensional star schema featuring dedicated surrogate keys, a pre-populated calendar dimension (`dim_date`), and an observation fact table (`fact_observation`) strictly enforcing atomic measurement grain.
3. **Automated Two-Stage ETL Pipeline**: An idempotent Python extraction, transformation, validation, and loading pipeline providing ACID transactional safety.
4. **Analytical SQL Engine & Geospatial Web Dashboard**: Advanced spatial queries (`ST_Intersection`, `ST_Contains`, `ST_Distance`), PL/pgSQL stored procedures, triggers, materialized views, window functions (`LAG`, rolling moving averages), and an interactive dark-mode dashboard.

---

## System Architecture

```
+-----------------------------------------------------------------------+
|                             DATA SOURCES                              |
|         Synthetic Multispectral & SAR Sensor Telemetry (CSV)          |
+-----------------------------------------------------------------------+
                                  |
                                  v  (Stage 1 ETL: Validation, Cleaning, ST_GeomFromText)
+-----------------------------------------------------------------------+
|                  OPERATIONAL SCHEMA (PostgreSQL + PostGIS)            |
|  • Normalized (3NF) Tables: satellite, sensor, region, observation,   |
|    image_data, land_cover, observation_land_cover, change_event       |
|  • PostGIS GiST (R-Tree) Indexes on 2D Polygon Boundaries/Footprints  |
|  • PL/pgSQL Stored Function: fn_compare_landcover()                   |
|  • Database Trigger & Audit Log: trg_audit_change_event               |
+-----------------------------------------------------------------------+
                                  |
                                  v  (Stage 2 ETL: Dimensional Extraction & Surrogate Key Join)
+-----------------------------------------------------------------------+
|                  DATA WAREHOUSE SCHEMA (Star Schema)                  |
|  • Fact Table: fact_observation (Grain: Obs × Region × Date × Cover)  |
|  • Dimensions: dim_satellite, dim_sensor, dim_region, dim_land_cover, |
|    dim_date (1,826 Pre-populated Calendar Days: 2021 to 2025)        |
|  • Materialized View: mvw_regional_quarterly_landcover                |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
|                     APPLICATION & ANALYTICS LAYER                     |
|  • FastAPI Backend Service (RESTful endpoints, SQL runner, CORS)      |
|  • Leaflet.js Interactive PostGIS Geospatial Map (CartoDB DarkMatter) |
|  • Chart.js OLAP Multi-dimensional Visualizations                     |
|  • Interactive SQL Viva Console with EXPLAIN ANALYZE Plan Visuals     |
|  • Live Architecture & Schema ERD Inspector                           |
+-----------------------------------------------------------------------+
```

---

## Key Technical Decisions for DBMS Evaluation

| Requirement | Implementation Detail | Technical Justification |
| :--- | :--- | :--- |
| **Normalization** | Operational Schema in **3NF** | Eliminates transitive dependencies $\text{obs} \to \text{sensor} \to \text{sat} \to \text{operator}$. Resolves $N:M$ observations to land covers via bridge entity `observation_land_cover`. |
| **Spatial Indexing** | PostGIS **GiST (R-Tree)** Indexes | Polygons lack a 1D scalar ordering. GiST indexes hierarchically group Minimum Bounding Boxes (MBR), pruning non-overlapping polygons in $O(\log N)$ time. |
| **Geodetic Accuracy** | `::geography` Casting | Planar `ST_Area` on SRID 4326 yields square degrees. Casting to `geography` evaluates true ellipsoidal surface area over the WGS84 spheroid in $\text{km}^2$. |
| **OLAP Star Schema** | Central `fact_observation` | Minimizes join depth during multi-dimensional slice/dice aggregations. Decouples operational keys using sequential surrogate keys. |
| **Fact Grain Enforcement** | Composite Unique Constraint | `UNIQUE (region_key, date_key, sensor_key, land_cover_key)` physically prevents duplicate metrics at the engine level. |
| **Window Functions** | `LAG()` and `ROWS BETWEEN` | Tracks Year-over-Year deforestation and computes smoothed 3-quarter rolling moving averages for urban expansion velocity. |
| **Database Programmability** | PL/pgSQL Stored Procedure & Trigger | `fn_compare_landcover` calculates land shifts in-database; `trg_audit_change_event` enforces auditability on data modifications. |
| **Performance Caching** | Materialized Views | `mvw_regional_quarterly_landcover` pre-computes heavy quarterly aggregations, cutting query latency from multi-table scans to sub-millisecond lookups. |

---

## Repository Directory Structure

```
satelite-change-detection/
│
├── backend/                             # FastAPI Application Server
│   ├── app/
│   │   ├── routes/
│   │   │   ├── changes.py              # Land cover shifts & stored procedure execution
│   │   │   ├── spatial.py              # PostGIS GeoJSON endpoints & spatial intersections
│   │   │   ├── sql_console.py          # Interactive SQL runner with EXPLAIN ANALYZE
│   │   │   ├── stats.py                # Global database metrics & schema metadata
│   │   │   └── warehouse.py            # OLAP endpoints: trends, urban expansion, sensors
│   │   ├── config.py                   # Environment configuration (.env loader)
│   │   ├── database.py                 # Threaded PostgreSQL connection pool (psycopg2)
│   │   └── main.py                     # FastAPI app factory, CORS & static frontend mount
│   ├── requirements.txt                # Python backend dependencies
│   └── run_server.py                   # Server startup script
│
├── frontend/                            # Modern Dark-Mode Dashboard SPA
│   ├── css/
│   │   └── styles.css                  # Custom cosmic glassmorphism design system
│   ├── js/
│   │   ├── app.js                      # UI navigation orchestrator & comparison runner
│   │   ├── charts.js                   # Chart.js OLAP graphs & window function visuals
│   │   ├── map.js                      # Leaflet.js PostGIS polygon visualizer
│   │   └── sql_console.js              # Interactive SQL preset loader & query executor
│   └── index.html                      # Complete single-page application interface
│
├── database/                            # SQL DDL, Dimensions, Analytics & Seeds
│   ├── schema/
│   │   ├── 01_tables.sql               # Operational 3NF tables & PostGIS extension
│   │   ├── 02_constraints.sql          # Primary, Foreign, and Check constraints
│   │   └── 03_indexes.sql              # GiST spatial and B-tree indexes
│   ├── warehouse/
│   │   ├── 01_dimensions.sql           # Star schema dimensions & dim_date calendar generator
│   │   ├── 02_fact.sql                 # Central fact_observation table & grain constraint
│   │   └── 03_indexes.sql              # Fact table surrogate foreign key indexes
│   ├── analytics/
│   │   ├── 01_spatial_queries.sql      # Advanced PostGIS analytical queries
│   │   ├── 02_olap_queries.sql         # ROLLUP, CUBE, and window queries
│   │   └── 03_views_and_procedures.sql # Materialized views, stored functions & audit triggers
│   ├── queries/                        # Standalone demonstration query scripts
│   │   ├── 01_operational_crud_and_3nf.sql
│   │   ├── 02_postgis_spatial_analysis.sql
│   │   ├── 03_data_warehouse_olap_rollup.sql
│   │   ├── 04_advanced_window_functions.sql
│   │   └── 05_stored_procedures_and_triggers.sql
│   └── seeds/
│       └── 01_reference_seeds.sql      # Core reference data SQL seeds
│
├── etl/                                 # Automated Two-Stage ETL Pipeline
│   ├── data/                           # Synthetic satellite telemetry CSV files
│   ├── scripts/
│   │   ├── generate_sample_data.py     # Deterministic telemetry generator
│   │   ├── stage1_operational_load.py  # 3NF operational extraction, cleaning & WKT load
│   │   └── stage2_warehouse_load.py    # Dimensional star schema transformation & load
│   ├── requirements.txt                # ETL requirements (pandas, numpy, psycopg2, shapely)
│   └── run_pipeline.py                 # Master ETL orchestrator & integrity audit reporter
│
├── docs/                                # Comprehensive Documentation Suite
│   ├── requirements.md                 # Software Requirements Specification (SRS) & Track C scope
│   ├── architecture.md                 # Two-tier hybrid architecture (3NF OLTP vs Star Schema OLAP)
│   ├── normalization.md                # FDs, 1NF, 2NF, 3NF mathematical proofs & denormalization notes
│   ├── er-diagram.md                   # Operational & Star Schema ERDs, cardinality matrix & media links
│   ├── warehouse.md                    # Fact grain, dimension surrogate keys, OLAP rollups & windowing
│   ├── api.md                          # RESTful endpoints directory & GeoJSON schema specifications
│   ├── viva.md                         # Viva examination prep, theoretical Q&A & engineering debugging logs
│   ├── 01_PROJECT_REPORT.md            # Academic project report & experimental findings
│   └── 03_ERD_AND_DATA_DICTIONARY.md   # Mermaid ERDs & exhaustive table data dictionary
│
├── docker-compose.yml                   # PostgreSQL 16 + PostGIS 3.4 container service (Port 5433:5432)
├── .env.example                         # Environment template with default port 5433
├── .env                                 # Database credentials & port configuration
└── README.md                            # Main project documentation
```

---

## Quickstart & Setup Guide

### 1. Prerequisites
- **Docker & Docker Compose** (for running the PostgreSQL + PostGIS container)
- **Python 3.11+**
- Modern Web Browser (Chrome, Edge, Firefox, Brave)

### 2. Launch the Database Service
Start the PostgreSQL 16 container with PostGIS 3.4 extensions:
```bash
docker compose up -d
```
The database starts on port `5433` (configured in `.env` to prevent conflicts with default Postgres ports).

### 3. Install Python Dependencies
```bash
pip install -r backend/requirements.txt
pip install -r etl/requirements.txt
```

### 4. Run the Master ETL Pipeline
Execute the idempotent ETL pipeline to validate, transform, and load telemetry data into both the 3NF operational schema and the dimensional star schema:
```bash
python etl/run_pipeline.py
```
*Optional: pass `--regenerate-data` to regenerate synthetic telemetry CSVs.*

### 5. Launch the Application Server
Start the FastAPI server:
```bash
python backend/run_server.py
```

### 6. Access the Interactive Dashboard
Open your browser and navigate to:
```
http://localhost:8000
```

---

## Dashboard Capabilities & Features

1. **Interactive Geospatial Map (Leaflet.js + PostGIS)**:
   - Visualizes monitored territory boundaries (Delhi NCR, Mumbai Metropolitan, Bengaluru Urban, Forest Belt, Punjab Basin, Eastern Coastal Estuary).
   - Dynamic overlay of satellite swath footprints (MSI, OLI-2, C-band SAR).
   - Real-time hover inspection displaying surface area, observation frequency, and detected change count.
2. **Land Cover Shift Calculator (Stored Procedure UI)**:
   - Dynamic selection of regions and baseline/evaluation observation dates.
   - Triggers `operational.fn_compare_landcover()` directly on the database engine.
   - Displays net shift in $\text{km}^2$ and percentage change with color-coded positive/negative badges.
3. **Data Warehouse & OLAP Analytics (Chart.js)**:
   - **Urban Expansion Velocity**: Rolling 3-quarter window moving average (`ROWS BETWEEN 2 PRECEDING AND CURRENT ROW`).
   - **Quarterly Land Cover Composition**: Stacked bar chart queried from the pre-computed materialized view.
   - **Sensor Throughput**: Total observed area and resolution comparison between optical and SAR radar instruments.
   - **Deforestation Index**: Annual forest cover loss tracked using the `LAG()` window function.
4. **Live Schema Inspector & ERD Viewer**:
   - Inspects live database tables, active row counters, column names, data types, and primary/foreign key flags.
5. **Interactive SQL Analytics Console**:
   - Curated analytical queries (PostGIS spatial overlap, Star schema ROLLUP, Window LAG, geodetic distances, sensor throughput).
   - Direct custom SQL query execution with read-only safety filters.
   - Integrated `EXPLAIN ANALYZE` execution plan visualizer displaying planning time, execution latency, and buffer memory hits.

---

## Documentation Links

- [Academic Project Report](docs/01_PROJECT_REPORT.md): In-depth report covering methodology, experimental results, and conclusions.
- [Project Walkthrough From Basics](docs/PROJECT_WALKTHROUGH_FROM_BASICS.md): Beginner-friendly, step-by-step conceptual guide explaining the entire project, architecture, and technology from scratch.
- [Entity-Relationship (ER) Diagrams](docs/ER_DIAGRAMS.md): Standalone ER models for the 3NF Operational Schema and Star Schema Data Warehouse.
- [Data Dictionary & Schema Details](docs/03_ERD_AND_DATA_DICTIONARY.md): Complete attribute registry and indexing specifications for all database relations.
