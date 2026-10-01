-- =============================================================================
-- SATELLITE DATA MANAGEMENT & GEOSPATIAL CHANGE DETECTION
-- Script: 01_reference_seeds.sql
-- Description: Core Reference Data Seeds (Satellites, Sensors, Regions, Land Cover)
-- Schema: operational
-- =============================================================================

SET search_path TO operational, public;

-- -----------------------------------------------------------------------------
-- 1. SATELLITES
-- -----------------------------------------------------------------------------
INSERT INTO operational.satellite (satellite_id, name, operator, launch_date, status) VALUES
(1, 'SYN-EO-1', 'Synthetic Earth Observation Program', '2015-03-12', 'active'),
(2, 'SYN-EO-2', 'Synthetic Earth Observation Program', '2018-07-01', 'active'),
(3, 'SYN-SAR-1', 'Synthetic Earth Observation Program', '2020-11-23', 'active')
ON CONFLICT (satellite_id) DO UPDATE 
SET name = EXCLUDED.name, operator = EXCLUDED.operator, launch_date = EXCLUDED.launch_date, status = EXCLUDED.status;

-- -----------------------------------------------------------------------------
-- 2. SENSORS
-- -----------------------------------------------------------------------------
INSERT INTO operational.sensor (sensor_id, satellite_id, name, sensor_type, resolution) VALUES
(1, 1, 'MultiSpectral-A', 'Optical', 10.00),
(2, 1, 'MultiSpectral-B', 'Optical', 20.00),
(3, 2, 'HighRes-Pan', 'Optical', 5.00),
(4, 2, 'MultiSpectral-C', 'Optical', 15.00),
(5, 3, 'SAR-C-Band', 'Radar', 25.00),
(6, 3, 'SAR-X-Band', 'Radar', 12.00)
ON CONFLICT (sensor_id) DO UPDATE 
SET name = EXCLUDED.name, sensor_type = EXCLUDED.sensor_type, resolution = EXCLUDED.resolution;

-- -----------------------------------------------------------------------------
-- 3. LAND COVER CLASSIFICATION CODES
-- -----------------------------------------------------------------------------
INSERT INTO operational.land_cover (land_cover_id, name, description) VALUES
(1, 'Forest', 'Dense tree canopy cover'),
(2, 'Urban', 'Built-up / impervious surface'),
(3, 'Water', 'Rivers, lakes, wetlands, reservoirs'),
(4, 'Agriculture', 'Cropland and cultivated land'),
(5, 'Barren', 'Bare soil / rock / unvegetated land')
ON CONFLICT (land_cover_id) DO UPDATE 
SET name = EXCLUDED.name, description = EXCLUDED.description;

-- -----------------------------------------------------------------------------
-- 4. MONITORED REGIONS (WGS84 Polygons SRID 4326)
-- -----------------------------------------------------------------------------
INSERT INTO operational.region (region_id, name, region_type, boundary) VALUES
(
    1, 'Delhi NCR', 'urban', 
    ST_GeomFromText('POLYGON((76.85 28.4, 77.35 28.4, 77.35 28.9, 76.85 28.9, 76.85 28.4))', 4326)
),
(
    2, 'Mumbai Metropolitan', 'urban', 
    ST_GeomFromText('POLYGON((72.75 18.9, 72.98 18.9, 72.98 19.3, 72.75 19.3, 72.75 18.9))', 4326)
),
(
    3, 'Bengaluru Urban', 'urban', 
    ST_GeomFromText('POLYGON((77.45 12.85, 77.75 12.85, 77.75 13.1, 77.45 13.1, 77.45 12.85))', 4326)
),
(
    4, 'Punjab Agricultural Belt (Synthetic)', 'agriculture', 
    ST_GeomFromText('POLYGON((75.0 30.2, 75.6 30.2, 75.6 30.8, 75.0 30.8, 75.0 30.2))', 4326)
),
(
    5, 'Central India Forest Belt (Synthetic)', 'forest', 
    ST_GeomFromText('POLYGON((80.0 21.0, 80.6 21.0, 80.6 21.6, 80.0 21.6, 80.0 21.0))', 4326)
),
(
    6, 'Eastern Coastal Wetland (Synthetic)', 'water', 
    ST_GeomFromText('POLYGON((86.3 20.4, 86.8 20.4, 86.8 20.9, 86.3 20.9, 86.3 20.4))', 4326)
)
ON CONFLICT (region_id) DO UPDATE 
SET name = EXCLUDED.name, region_type = EXCLUDED.region_type, boundary = EXCLUDED.boundary;

-- Reset sequence IDs
SELECT setval('operational.satellite_satellite_id_seq', (SELECT max(satellite_id) FROM operational.satellite));
SELECT setval('operational.sensor_sensor_id_seq', (SELECT max(sensor_id) FROM operational.sensor));
SELECT setval('operational.land_cover_land_cover_id_seq', (SELECT max(land_cover_id) FROM operational.land_cover));
SELECT setval('operational.region_region_id_seq', (SELECT max(region_id) FROM operational.region));
