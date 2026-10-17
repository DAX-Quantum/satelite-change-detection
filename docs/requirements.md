# Software Requirements Specification (SRS)
## Satellite Data Management and Geospatial Change Detection System
**Course:** DBMS Laboratory Course Project  
**Selected Track:** Track C — Data Warehouse and Analytics  

---

## 1. Problem Statement
Rapid urbanization, deforestation, agricultural shifts, and water body shrinkage require robust historical monitoring. Satellite earth observation systems generate multi-temporal spatial data. Traditional transactional databases struggle with complex spatial topology and multi-dimensional analytical queries simultaneously. 

This project solves this challenge by engineering a **two-tier hybrid database architecture**:
1. An **Operational Relational Database (OLTP)** modeled in **Third Normal Form (3NF)** with PostGIS extensions to ensure ACID transaction consistency, zero data anomalies, and strict spatial indexing.
2. A **Data Warehouse (OLAP)** structured as a **Star Schema** with surrogate keys and pre-aggregated dimensional hierarchies to enable sub-second analytical aggregations, historical trend computations, and geospatial change detection.

---

## 2. Project Objectives
- **Relational Integrity:** Model and normalize satellite observations up to 3NF, eliminating insertion, deletion, and update anomalies.
- **Geospatial Processing:** Integrate PostgreSQL 16 with PostGIS 3.4 to handle geographic boundaries (`GEOMETRY(POLYGON, 4326)`), calculate geodetic surface areas via `geography` casting, and execute spatial intersections (`ST_Intersects`).
- **Data Warehousing & Star Schema:** Build a dimensional model centered on an explicit grain: *One land-cover measurement, for one observation pass, in one region, on one calendar date*.
- **ETL Pipelines:** Construct robust, idempotent two-stage Python ETL pipelines:
  - *Stage 1:* Ingestion, validation, coordinate transformation, and bulk load into `operational`.
  - *Stage 2:* Star-schema extraction, surrogate key lookups, and load into `warehouse.fact_observation`.
- **Advanced SQL Analytics:** Implement multi-dimensional rollups (`ROLLUP`), analytical window functions (`LAG`, `ROWS PRECEDING`), and stored procedures for change detection.
- **API & Dynamic Web Dashboard:** Provide an interactive, vibrant web interface for querying metrics, viewing PostGIS maps, comparing land-cover shifts, and running viva demonstration SQL queries.

---

## 3. Functional Requirements

### FR-1: Satellite & Sensor Management
- The system shall store satellites with metadata: name, operator (e.g. ISRO, ESA, NASA), launch date, and operational status (`active`, `inactive`, `decommissioned`).
- The system shall associate each satellite with multiple sensors having distinct spatial resolutions (meters/pixel) and modalities (`Optical`, `Radar SAR`).

### FR-2: Spatial Region & Observation Tracking
- The system shall store geographic boundaries for monitored regions in WGS84 coordinate reference system (EPSG:4326).
- The system shall record satellite observation passes with acquisition dates, image references, and exact footprint coverage polygons.
- All spatial geometries must be indexed using GiST (Generalized Search Tree) indexes for high-performance spatial querying.

### FR-3: Land Cover Classification & Associative Measurements
- The system shall maintain standardized land-cover classes: `Forest`, `Urban`, `Water`, `Agriculture`, and `Barren`.
- Observation land-cover measurements shall be resolved via an associative entity (`observation_land_cover`) with composite primary key `(observation_id, land_cover_id)` to satisfy 1NF and 2NF.

### FR-4: Change Detection & Shift Computation
- The system shall calculate historical transitions between land-cover classes across distinct observation timestamps.
- The system shall record change events (`change_event`) capturing the from-class, to-class, duration, and shifted area in square meters.
- A PL/pgSQL stored procedure (`fn_compare_landcover`) shall compute baseline vs evaluation date percentage changes.

### FR-5: Star Schema Dimensional Analytics
- The data warehouse shall maintain 5 dimension tables: `dim_satellite`, `dim_sensor`, `dim_region`, `dim_date`, and `dim_land_cover`.
- `dim_date` shall be pre-populated across calendar years 2021–2025 using PostgreSQL `GENERATE_SERIES`.
- Fact table `fact_observation` shall enforce grain uniqueness via `UNIQUE (region_key, date_key, sensor_key, land_cover_key)`.

---

## 4. Non-Functional Requirements
- **Data Integrity:** Strict foreign key constraints with `ON DELETE RESTRICT` / `CASCADE`, domain check constraints (`resolution > 0`, `area >= 0`, `status IN (...)`).
- **Performance:** Spatial queries must utilize GiST bounding box filtering before evaluating exact geometry functions (`ST_Intersects`, `ST_Contains`).
- **Portability & Isolation:** Containerized PostgreSQL 16 + PostGIS 3.4 using Docker Compose. Host port configured to default to `5433` to prevent conflicts with native local PostgreSQL installations.
- **Security & Parameterization:** Parameterized queries across all backend routes to completely neutralize SQL injection vulnerabilities.
- **Explainability:** Clear, documented SQL schemas designed for second-year undergraduate DBMS course defense and viva examinations.
