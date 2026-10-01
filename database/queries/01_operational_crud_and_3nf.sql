-- =============================================================================
-- SATELLITE DATA MANAGEMENT & GEOSPATIAL CHANGE DETECTION
-- Script: 01_operational_crud_and_3nf.sql
-- Description: Operational 3NF Schema Verification, Joins, and Referential Integrity
-- Schema: operational
-- =============================================================================

SET search_path TO operational, public;

-- -----------------------------------------------------------------------------
-- 1. Full Multi-Table Normalized Join (Satellites -> Sensors -> Observations)
-- Demonstrates 3NF decomposition where satellite metadata is normalized out of sensor
-- -----------------------------------------------------------------------------
SELECT 
    s.satellite_id,
    s.name AS satellite_name,
    s.operator,
    se.sensor_id,
    se.name AS sensor_name,
    se.sensor_type,
    se.resolution AS resolution_meters,
    o.observation_id,
    o.observation_date,
    o.image_reference,
    r.name AS region_name,
    r.region_type
FROM operational.satellite s
JOIN operational.sensor se ON s.satellite_id = se.satellite_id
JOIN operational.observation o ON se.sensor_id = o.sensor_id
JOIN operational.region r ON o.region_id = r.region_id
ORDER BY o.observation_date DESC, s.name
LIMIT 15;


-- -----------------------------------------------------------------------------
-- 2. Many-to-Many Land Cover Breakdown per Observation Pass
-- Demonstrates the bridge entity `observation_land_cover` resolving N:M
-- -----------------------------------------------------------------------------
SELECT 
    o.observation_id,
    o.observation_date,
    r.name AS region_name,
    lc.name AS land_cover_class,
    ROUND((olc.area / 1000000.0)::numeric, 2) AS measured_area_sq_km,
    ROUND((olc.area / NULLIF(SUM(olc.area) OVER (PARTITION BY o.observation_id), 0) * 100.0)::numeric, 1) AS percentage_of_pass
FROM operational.observation o
JOIN operational.region r ON o.region_id = r.region_id
JOIN operational.observation_land_cover olc ON o.observation_id = olc.observation_id
JOIN operational.land_cover lc ON olc.land_cover_id = lc.land_cover_id
WHERE r.name = 'Delhi NCR'
ORDER BY o.observation_date DESC, olc.area DESC
LIMIT 15;


-- -----------------------------------------------------------------------------
-- 3. High-Resolution Imagery Assets Joined to Sensor Acquisitions
-- Demonstrates 1:1 and 1:N integrity between Observation passes and Imagery files
-- -----------------------------------------------------------------------------
SELECT 
    img.image_id,
    o.observation_id,
    r.name AS region_name,
    s.name AS satellite_name,
    img.file_reference,
    img.format,
    ROUND((img.file_size / (1024.0 * 1024.0))::numeric, 2) AS file_size_mb,
    img.acquisition_time
FROM operational.image_data img
JOIN operational.observation o ON img.observation_id = o.observation_id
JOIN operational.region r ON o.region_id = r.region_id
JOIN operational.sensor se ON o.sensor_id = se.sensor_id
JOIN operational.satellite s ON se.satellite_id = s.satellite_id
ORDER BY img.acquisition_time DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- 4. Referential Integrity & Foreign Key Constraint Audit
-- Verifies no orphan records exist across any foreign key relationships
-- -----------------------------------------------------------------------------
SELECT 
    'Orphan Sensors' AS check_name,
    COUNT(*) AS orphan_count
FROM operational.sensor se
LEFT JOIN operational.satellite s ON se.satellite_id = s.satellite_id
WHERE s.satellite_id IS NULL

UNION ALL

SELECT 
    'Orphan Observations' AS check_name,
    COUNT(*) AS orphan_count
FROM operational.observation o
LEFT JOIN operational.sensor se ON o.sensor_id = se.sensor_id
WHERE se.sensor_id IS NULL

UNION ALL

SELECT 
    'Orphan Observation Land Covers' AS check_name,
    COUNT(*) AS orphan_count
FROM operational.observation_land_cover olc
LEFT JOIN operational.observation o ON olc.observation_id = o.observation_id
WHERE o.observation_id IS NULL;
