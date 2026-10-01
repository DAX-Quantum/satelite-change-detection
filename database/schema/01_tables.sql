-- =========================================================
-- 01_tables.sql
-- Satellite Data Management & Geospatial Change Detection
-- Operational schema: table definitions (3NF)
-- =========================================================

CREATE SCHEMA IF NOT EXISTS operational;
SET search_path TO operational, public;

-- PostGIS must be enabled once per database (not per schema).
-- Pinned explicitly to the "public" schema: public is in every
-- session's default search_path, so functions like
-- ST_GeomFromText(...) stay callable unqualified from ANY
-- connection (e.g. the Python ETL script's connection, which does
-- not set search_path) -- not just from a session that happens to
-- have "operational" in its search_path.
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA public;

-- ---------------------------------------------------------
-- SATELLITE
-- ---------------------------------------------------------
CREATE TABLE satellite (
    satellite_id    SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    operator        VARCHAR(100),
    launch_date     DATE,
    status          VARCHAR(20)
);

-- ---------------------------------------------------------
-- SENSOR  (1 satellite -> N sensors)
-- ---------------------------------------------------------
CREATE TABLE sensor (
    sensor_id       SERIAL PRIMARY KEY,
    satellite_id    INTEGER NOT NULL REFERENCES satellite(satellite_id),
    name            VARCHAR(100) NOT NULL,
    sensor_type     VARCHAR(50),
    resolution      NUMERIC(10,2)   -- meters per pixel
);

-- ---------------------------------------------------------
-- REGION  (spatial: a polygon boundary)
-- ---------------------------------------------------------
CREATE TABLE region (
    region_id       SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    region_type     VARCHAR(50),
    boundary        GEOMETRY(POLYGON, 4326) NOT NULL
);

-- ---------------------------------------------------------
-- OBSERVATION  (1 sensor -> N observations, 1 region -> N observations)
-- ---------------------------------------------------------
CREATE TABLE observation (
    observation_id      SERIAL PRIMARY KEY,
    sensor_id            INTEGER NOT NULL REFERENCES sensor(sensor_id),
    region_id             INTEGER NOT NULL REFERENCES region(region_id),
    observation_date       DATE NOT NULL,
    image_reference         VARCHAR(255),
    footprint                GEOMETRY(POLYGON, 4326) NOT NULL
);

-- ---------------------------------------------------------
-- IMAGE_DATA  (1 observation -> N image files/bands)
-- ---------------------------------------------------------
CREATE TABLE image_data (
    image_id            SERIAL PRIMARY KEY,
    observation_id        INTEGER NOT NULL REFERENCES observation(observation_id),
    file_reference          VARCHAR(255) NOT NULL,
    format                    VARCHAR(20),
    file_size                  BIGINT,
    acquisition_time             TIMESTAMP
);

-- ---------------------------------------------------------
-- LAND_COVER  (lookup table: Forest, Urban, Water, ...)
-- ---------------------------------------------------------
CREATE TABLE land_cover (
    land_cover_id   SERIAL PRIMARY KEY,
    name            VARCHAR(50) NOT NULL UNIQUE,
    description     TEXT
);

-- ---------------------------------------------------------
-- OBSERVATION_LAND_COVER (associative table resolving N:M)
-- ---------------------------------------------------------
CREATE TABLE observation_land_cover (
    observation_id  INTEGER NOT NULL REFERENCES observation(observation_id),
    land_cover_id   INTEGER NOT NULL REFERENCES land_cover(land_cover_id),
    area            NUMERIC(14,2) NOT NULL,   -- sq. meters, measured for THIS pairing
    PRIMARY KEY (observation_id, land_cover_id)
);

-- ---------------------------------------------------------
-- CHANGE_EVENT (a region's land cover changing from X to Y over time)
-- ---------------------------------------------------------
CREATE TABLE change_event (
    change_id           SERIAL PRIMARY KEY,
    region_id             INTEGER NOT NULL REFERENCES region(region_id),
    from_land_cover_id      INTEGER NOT NULL REFERENCES land_cover(land_cover_id),
    to_land_cover_id          INTEGER NOT NULL REFERENCES land_cover(land_cover_id),
    start_date                  DATE NOT NULL,
    end_date                      DATE NOT NULL,
    changed_area                    NUMERIC(14,2) NOT NULL
);
