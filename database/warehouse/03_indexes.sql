-- =========================================================
-- 03_indexes.sql
-- Data Warehouse: FK indexes on the fact table
-- =========================================================
-- Every OLAP query joins FACT_OBSERVATION to one or more
-- dimensions and/or filters by one of these keys (e.g. "trend
-- for region X", "all observations in Q1 2023"). Without these
-- indexes, each such join is a sequential scan of the whole fact
-- table as it grows.
-- =========================================================

SET search_path TO warehouse, public;

CREATE INDEX idx_fact_satellite_key   ON fact_observation(satellite_key);
CREATE INDEX idx_fact_sensor_key      ON fact_observation(sensor_key);
CREATE INDEX idx_fact_region_key      ON fact_observation(region_key);
CREATE INDEX idx_fact_date_key        ON fact_observation(date_key);
CREATE INDEX idx_fact_land_cover_key  ON fact_observation(land_cover_key);
