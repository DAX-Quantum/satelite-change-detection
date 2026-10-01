-- =========================================================
-- 02_fact.sql
-- Data Warehouse: fact table (star schema)
-- =========================================================
--
-- GRAIN (explicit, per Section 8 of the architecture doc):
-- One fact row = one land-cover measurement, for one satellite
-- observation, in one region, on one date.
-- i.e. the grain matches one row of operational.observation_land_cover,
-- enriched with dimension keys instead of raw operational FKs.
-- =========================================================

SET search_path TO warehouse, public;

CREATE TABLE fact_observation (
    observation_fact_key    SERIAL PRIMARY KEY,
    satellite_key           INTEGER NOT NULL REFERENCES dim_satellite(satellite_key),
    sensor_key              INTEGER NOT NULL REFERENCES dim_sensor(sensor_key),
    region_key              INTEGER NOT NULL REFERENCES dim_region(region_key),
    date_key                INTEGER NOT NULL REFERENCES dim_date(date_key),
    land_cover_key          INTEGER NOT NULL REFERENCES dim_land_cover(land_cover_key),
    area                    NUMERIC(14,2) NOT NULL CHECK (area >= 0),
    observation_count       INTEGER NOT NULL DEFAULT 1 CHECK (observation_count >= 0),

    -- Prevents duplicate fact rows if the warehouse ETL is re-run
    -- without a TRUNCATE first -- enforces the grain at the DB level,
    -- not just by convention.
    CONSTRAINT uq_fact_grain UNIQUE (region_key, date_key, sensor_key, land_cover_key)
);
