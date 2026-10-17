# REST API Documentation
## Satellite Data Management and Geospatial Change Detection System
**Track C — Data Warehouse and Analytics**

---

## 1. Overview & Architectural Principles
- **Base URL:** `http://localhost:8000/api`
- **Database Aggregation:** All statistical calculations, windowing, spatial transformations, and aggregations occur directly within the PostgreSQL/PostGIS database engine, never in application memory.
- **Spatial Geometry:** Boundaries and footprints are formatted dynamically using PostGIS `ST_AsGeoJSON` and delivered as standard RFC 7946 GeoJSON FeatureCollections.
- **Security:** 100% parameterized SQL queries (`%s`). Direct string interpolation is strictly banned.

---

## 2. API Endpoints Directory

### Core Analytical Endpoints

#### `GET /api/dashboard/summary`
Returns top-level metric counters across operational and warehouse schemas.
- **Response `200 OK`:**
  ```json
  {
    "total_satellites": 3,
    "total_sensors": 6,
    "total_regions": 6,
    "total_observations": 96,
    "total_change_events": 18,
    "total_fact_rows": 480,
    "total_dim_dates": 1826,
    "total_changed_area_sq_km": 1183.50,
    "database_size": "26 MB"
  }
  ```

#### `GET /api/satellites`
Returns all satellites, operational status, and associated sensors.
- **Response `200 OK`:** Array of satellite objects:
  ```json
  [
    {
      "satellite_id": 1,
      "name": "SYN-EO-1",
      "operator": "ISRO",
      "launch_date": "2020-11-07",
      "status": "active",
      "sensor_count": 2
    }
  ]
  ```

#### `GET /api/sensors`
Returns sensors with host satellite info and ground resolution (m/pixel).
- **Response `200 OK`:** Array of sensor objects.

#### `GET /api/regions`
Returns monitored regions with PostGIS geographic area (km²) and GeoJSON boundary.
- **Response `200 OK`:** Array of region objects with embedded GeoJSON coordinates.

#### `GET /api/observations`
Returns satellite observation passes.
- **Query Parameters:**
  - `region_id` (optional, integer): Filter by region.
  - `sensor_id` (optional, integer): Filter by sensor.
  - `limit` (optional, integer, default: 100): Maximum rows to return.

#### `GET /api/land-cover/trends`
Queries the warehouse star schema for multi-temporal land cover distributions.
- **Query Parameters:**
  - `region_id` (optional, integer): Filter by natural region ID.
- **Response `200 OK`:** Array of quarterly measurements with period label (`YYYY-QX`) and area in km².

#### `GET /api/changes`
Returns detected historical land-cover change events.
- **Query Parameters:**
  - `region_id` (optional, integer): Filter by region.

#### `GET /api/analytics/satellites`
Returns observation volume, operational coverage, and sensor counts per satellite.

#### `GET /api/analytics/sensors`
Returns observation load and total captured surface area (km²) grouped by sensor.

#### `GET /api/analytics/regions`
Returns observation density, physical geographic area, and total shifted land area per region.

#### `GET /api/geospatial/observations`
Returns satellite observation footprint polygons formatted as GeoJSON.
- **Query Parameters:**
  - `region_id` (optional, integer)
  - `limit` (optional, integer, default: 50)
- **Response `200 OK`:** Standard GeoJSON `FeatureCollection`.

#### `GET /api/regions/{id}/analysis`
Returns a deep-dive analytical profile for a specific region:
- Spatial centroid and boundary GeoJSON
- Multi-year land cover evolution timeline
- Historical detected change events
- Observation cadence and date range

---

### Interactive Viva & Console Endpoints

#### `GET /api/sql/viva-queries`
Returns curated viva demonstration queries covering 3NF operations, PostGIS spatial queries, OLAP rollups, window functions, and stored procedures.

#### `POST /api/sql/execute`
Executes safe read-only SQL queries against the database with strict blocklists (`DROP`, `TRUNCATE`, `DELETE`, `UPDATE` blocked).
- **Request Body:**
  ```json
  { "sql": "SELECT name, resolution FROM operational.sensor;" }
  ```
- **Response `200 OK`:**
  ```json
  {
    "columns": ["name", "resolution"],
    "rows": [...],
    "row_count": 6,
    "execution_time_ms": 1.42
  }
  ```

#### `POST /api/sql/explain`
Runs `EXPLAIN (ANALYZE, COSTS, BUFFERS)` to inspect PostgreSQL execution plans and index usage (e.g. GiST bounding box tree vs sequential scans).
