-- =========================================================
-- 03_indexes.sql
-- Foreign-key indexes + PostGIS spatial (GiST) indexes
-- =========================================================

SET search_path TO operational, public;

-- ---------------------------------------------------------
-- FK indexes
-- PostgreSQL does NOT auto-index foreign key columns
-- (unlike the primary key side). Without these, every join
-- and every "delete parent row" FK-check does a sequential
-- scan on the child table as it grows.
-- ---------------------------------------------------------
CREATE INDEX idx_sensor_satellite_id        ON sensor(satellite_id);
CREATE INDEX idx_observation_sensor_id       ON observation(sensor_id);
CREATE INDEX idx_observation_region_id        ON observation(region_id);
CREATE INDEX idx_observation_date              ON observation(observation_date);
CREATE INDEX idx_image_data_observation_id       ON image_data(observation_id);
CREATE INDEX idx_olc_land_cover_id                ON observation_land_cover(land_cover_id);
CREATE INDEX idx_change_event_region_id            ON change_event(region_id);
CREATE INDEX idx_change_event_from_lc               ON change_event(from_land_cover_id);
CREATE INDEX idx_change_event_to_lc                  ON change_event(to_land_cover_id);

-- ---------------------------------------------------------
-- Spatial (GiST) indexes
-- B-tree indexes cannot accelerate spatial predicates like
-- ST_Intersects / ST_Contains / ST_DWithin. GiST builds a
-- bounding-box tree over the geometries so PostGIS can throw
-- away non-overlapping candidates before doing exact geometry
-- math -- this is what makes spatial queries fast at scale.
-- ---------------------------------------------------------
CREATE INDEX idx_region_boundary_gist        ON region      USING GIST (boundary);
CREATE INDEX idx_observation_footprint_gist   ON observation USING GIST (footprint);
