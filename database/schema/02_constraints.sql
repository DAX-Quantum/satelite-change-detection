-- =========================================================
-- 02_constraints.sql
-- Additional CHECK / UNIQUE constraints
-- (PK, FK, NOT NULL are already defined in 01_tables.sql)
-- =========================================================

SET search_path TO operational, public;

-- SATELLITE: status must be one of a known set of values
ALTER TABLE satellite
    ADD CONSTRAINT chk_satellite_status
    CHECK (status IN ('active', 'inactive', 'decommissioned'));

-- SENSOR: resolution must be a positive number (meters/pixel)
ALTER TABLE sensor
    ADD CONSTRAINT chk_sensor_resolution
    CHECK (resolution IS NULL OR resolution > 0);

-- SENSOR: a satellite should not have two sensors with the same name
ALTER TABLE sensor
    ADD CONSTRAINT uq_sensor_name_per_satellite
    UNIQUE (satellite_id, name);

-- IMAGE_DATA: file size cannot be negative
ALTER TABLE image_data
    ADD CONSTRAINT chk_image_file_size
    CHECK (file_size IS NULL OR file_size >= 0);

-- OBSERVATION_LAND_COVER: area cannot be negative
ALTER TABLE observation_land_cover
    ADD CONSTRAINT chk_olc_area
    CHECK (area >= 0);

-- CHANGE_EVENT: changed_area cannot be negative
ALTER TABLE change_event
    ADD CONSTRAINT chk_change_area
    CHECK (changed_area >= 0);

-- CHANGE_EVENT: end_date must not be before start_date
ALTER TABLE change_event
    ADD CONSTRAINT chk_change_dates
    CHECK (end_date >= start_date);

-- CHANGE_EVENT: a "change" must actually be between two DIFFERENT land covers
ALTER TABLE change_event
    ADD CONSTRAINT chk_change_different_landcover
    CHECK (from_land_cover_id <> to_land_cover_id);
