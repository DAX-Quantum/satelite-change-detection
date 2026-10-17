# Viva Voce Examination & Defense Preparation Guide
## Satellite Data Management and Geospatial Change Detection System
**Course:** DBMS Laboratory Course Project  
**Selected Track:** Track C — Data Warehouse and Analytics  

---

## 1. Core Database Theory & Relational Design

### Q1: Why PostgreSQL instead of MySQL or MongoDB?
- **PostgreSQL** provides native, enterprise-grade spatial capabilities via **PostGIS**, superior window functions (`LAG`, `LEAD`, `ROWS BETWEEN`), advanced grouping sets (`ROLLUP`, `CUBE`), multi-schema logical partitioning (`operational` vs `warehouse`), and true transactional DDL (`CREATE/ALTER/DROP` run safely inside atomic transactions).
- **MySQL** has limited spatial functions compared to PostGIS (which supports GEOGRAPHY ellipsoidal geodetics, 3D geometries, raster analysis) and lacks PostgreSQL's sophisticated query planner for dimensional analytics.
- **MongoDB (NoSQL)** lacks declarative referential integrity (FKs), ACID transactions across complex relationships, relational normalization, and native spatial indexing with spherical geodetic surface calculations.

### Q2: Why normalize to 3NF in the operational database?
- **Third Normal Form (3NF)** eliminates redundancy and prevents insertion, update, and deletion anomalies.
- For example, if satellite details were embedded in `observation`, decommissioning a satellite would require updating thousands of rows. In 3NF, the update occurs in exactly one row in `satellite`.

### Q3: Why is the associative table `OBSERVATION_LAND_COVER` necessary?
- There is an **N:M (Many-to-Many) relationship** between `OBSERVATION` and `LAND_COVER`.
- One satellite observation image covers multiple land-cover classes (Forest, Urban, Water).
- Conversely, each land-cover class appears in multiple observations across different dates and regions.
- In relational database theory, an N:M relationship cannot be represented directly using single foreign keys without violating 1NF (storing multi-valued comma strings) or duplicating observation rows. The associative entity resolves this into two clean 1:N relationships.

### Q4: What is the composite key in `OBSERVATION_LAND_COVER`?
- The primary key is **`(observation_id, land_cover_id)`**.
- The non-key attribute `area` functionally depends on the **entire composite key**, not on either column individually. This guarantees 2NF compliance.

### Q5: Why not use a single giant table?
- A single denormalized table would cause massive data duplication (e.g. repeating satellite names, sensor specs, and region polygons for every single observation row).
- This introduces severe update anomalies, wastes storage, slows down operational transaction processing, and increases the risk of inconsistent data.

---

## 2. Data Warehouse & Dimensional Modeling (OLAP)

### Q6: What is the difference between OLTP and OLAP?
| Feature | OLTP (`operational`) | OLAP (`warehouse`) |
| :--- | :--- | :--- |
| **Workload** | Frequent reads, inserts, and updates | High-throughput analytical batch reads |
| **Data Structure** | Highly normalized (3NF) | Denormalized (Star Schema) |
| **Keys** | Natural primary keys & composite PKs | Surrogate integer keys (`*_key SERIAL`) |
| **Query Complexity** | Simple lookups with targeted joins | Multi-level aggregations, rollups, windowing |
| **Historical Data** | Current transactional snapshot | Multi-year historical time-series |

### Q7: What is the exact grain of `FACT_OBSERVATION`?
> **"One fact row represents one land-cover measurement for one satellite observation in one region on one date."**  
Each row contains five foreign keys referencing the dimensions (`satellite_key`, `sensor_key`, `region_key`, `date_key`, `land_cover_key`) and numerical measures (`area` in m², `observation_count`).

### Q8: How is the grain enforced in PostgreSQL?
Through a database-level unique constraint:
```sql
CONSTRAINT uq_fact_grain UNIQUE (region_key, date_key, sensor_key, land_cover_key)
```
If an ETL script accidentally attempts to insert duplicate measurements, PostgreSQL raises a unique constraint violation instead of silently double-counting areas.

### Q9: Why use surrogate keys in dimensions instead of operational primary keys?
1. **Lifecycle Decoupling:** The warehouse refreshes on its own batch schedule. If operational records are archived, deleted, or re-indexed, the warehouse analytical history remains intact.
2. **Standardization:** Integer surrogate keys (`INT`) provide consistent, high-speed joins regardless of how source IDs are structured.
3. **Traceability:** The natural operational ID (e.g. `satellite_id`) is stored as a plain audit column without a foreign key constraint back to `operational`.

### Q10: Why pre-populate `dim_date` using `GENERATE_SERIES`?
- Pre-calculating calendar attributes (`year`, `quarter`, `month`, `month_name`, `day`) for 1,826 days (2021–2025) avoids CPU-intensive date extraction functions during real-time queries.
- Outer joins with `dim_date` reveal missing observation dates or temporal gaps in satellite coverage.

---

## 3. Geospatial & PostGIS Technical Details

### Q11: What is SRID 4326? Why is it used?
- **SRID 4326** refers to the **WGS 84 (World Geodetic System 1984)** spatial reference system.
- It is the global standard reference coordinate system used by GPS and satellite imagery, expressing coordinates in longitude and latitude on the WGS 84 ellipsoid.

### Q12: Why cast to `geography` when calculating area or distance?
- In `geometry(Polygon, 4326)`, coordinates are in **degrees**. Calculating `ST_Area` directly on degrees produces square degrees, which is mathematically invalid for physical area calculations because degrees of longitude converge toward the poles.
- Casting to `geography` (`ST_Area(geom::geography)`) instructs PostGIS to compute true geodetic surface areas on the curved WGS 84 ellipsoid in **square meters ($m^2$)**.

### Q13: What is a GiST index and how does spatial intersection work?
- **GiST (Generalized Search Tree):** Builds a bounding-box R-tree over polygon geometries.
- **Two-phase spatial query execution:**
  1. *Filter Phase (Index Scan):* PostgreSQL compares the bounding boxes (Minimum Bounding Rectangles - MBR) using the GiST index in $O(\log N)$ time, instantly discarding 99% of non-candidate polygons.
  2. *Refinement Phase (Exact Evaluation):* PostGIS runs exact computational geometry algorithms (`ST_Intersects`) only on the small candidate subset.

---

## 4. Real Engineering Challenges & Debugging Stories (Viva Highlights)

### Story 1: Host Port Conflict (Port 5432 vs. 5433)
- **Challenge:** Initial attempts to connect to PostgreSQL failed with `password authentication failed`, despite using the correct password.
- **Diagnosis:** A local native PostgreSQL instance was already running on host port `5432`, intercepting the connection before Docker could receive it.
- **Resolution:** Mapped the container to host port `5433` via `.env` (`"${POSTGRES_PORT:-5433}:5432"`). The container listens on 5432 internally, but the host accesses it cleanly via 5433.

### Story 2: Composite Primary Key Deduplication in ETL
- **Challenge:** Early ETL deduplication logic deduped on `observation_id` alone.
- **Diagnosis:** `observation_land_cover` has a composite primary key `(observation_id, land_cover_id)`. Deduping on `observation_id` silently deleted valid land cover rows, leaving only 1 land cover class per observation instead of all 5!
- **Resolution:** Configured pandas deduplication strictly on `subset=['observation_id', 'land_cover_id']`, restoring the full 480 fact measurements.

### Story 3: PostGIS Extension Schema Placement
- **Challenge:** Creating the PostGIS extension inside schema `operational` caused `ST_GeomFromText` calls from other connections (e.g. Stage 2 ETL or default sessions) to fail with `function does not exist`.
- **Diagnosis:** PostgreSQL sessions that do not have `operational` in their `search_path` cannot find spatial functions if installed in `operational`.
- **Resolution:** Pinned PostGIS explicitly to `public`:
  ```sql
  CREATE EXTENSION IF NOT EXISTS postgis SCHEMA public;
  ```
  Since `public` is included in every session's default `search_path`, all spatial functions are globally accessible unqualified from any database connection.
