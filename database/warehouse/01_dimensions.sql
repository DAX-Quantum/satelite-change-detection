-- =========================================================
-- 01_dimensions.sql
-- Data Warehouse: dimension tables (star schema)
-- =========================================================
--
-- DESIGN NOTE: dimension tables use their OWN surrogate keys
-- (satellite_key, sensor_key, ...) rather than reusing the
-- operational database's primary keys directly. The natural key
-- (e.g. satellite_id) is kept as a plain column for traceability,
-- but is NOT a foreign key back into the operational schema.
-- This is intentional: the warehouse is refreshed on its own
-- schedule by its own ETL stage, and should not be hard-wired to
-- operational table lifecycles (a classic OLTP vs OLAP separation
-- point -- good viva material).
-- =========================================================

CREATE SCHEMA IF NOT EXISTS warehouse;
SET search_path TO warehouse, public;

-- ---------------------------------------------------------
-- DIM_SATELLITE
-- ---------------------------------------------------------
CREATE TABLE dim_satellite (
    satellite_key   SERIAL PRIMARY KEY,
    satellite_id    INTEGER NOT NULL,      -- natural key (traceability only)
    name            VARCHAR(100) NOT NULL,
    operator        VARCHAR(100),
    status          VARCHAR(20)
);

-- ---------------------------------------------------------
-- DIM_SENSOR
-- ---------------------------------------------------------
CREATE TABLE dim_sensor (
    sensor_key      SERIAL PRIMARY KEY,
    sensor_id       INTEGER NOT NULL,
    name            VARCHAR(100) NOT NULL,
    sensor_type     VARCHAR(50),
    resolution      NUMERIC(10,2)
);

-- ---------------------------------------------------------
-- DIM_REGION
-- ---------------------------------------------------------
CREATE TABLE dim_region (
    region_key      SERIAL PRIMARY KEY,
    region_id       INTEGER NOT NULL,
    name            VARCHAR(100) NOT NULL,
    region_type     VARCHAR(50)
);

-- ---------------------------------------------------------
-- DIM_LAND_COVER
-- ---------------------------------------------------------
CREATE TABLE dim_land_cover (
    land_cover_key  SERIAL PRIMARY KEY,
    land_cover_id   INTEGER NOT NULL,
    name            VARCHAR(50) NOT NULL
);

-- ---------------------------------------------------------
-- DIM_DATE
-- Pre-populated with one row per calendar date in the project's
-- data range. date_key is a human-readable surrogate (YYYYMMDD
-- as an integer) -- a common, deliberate star-schema convention:
-- it sorts correctly, is still a surrogate (not a natural key
-- tied to any source system), and is easy to read while debugging.
-- ---------------------------------------------------------
CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,      -- e.g. 20230415
    full_date       DATE NOT NULL UNIQUE,
    day             INTEGER NOT NULL,
    month           INTEGER NOT NULL,
    month_name      VARCHAR(20) NOT NULL,
    quarter         INTEGER NOT NULL,
    year            INTEGER NOT NULL
);

-- Populate DIM_DATE for 2021-01-01 .. 2025-12-31 (covers the
-- synthetic data's 2021-2024 range with headroom for new data).
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
