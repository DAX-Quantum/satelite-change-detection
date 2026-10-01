-- =============================================================================
-- SATELLITE DATA MANAGEMENT & GEOSPATIAL CHANGE DETECTION
-- Script: 03_data_warehouse_olap_rollup.sql
-- Description: Star Schema Multi-Dimensional OLAP Queries (ROLLUP, CUBE, GROUPING SETS)
-- Schema: warehouse
-- =============================================================================

SET search_path TO warehouse, public;

-- -----------------------------------------------------------------------------
-- 1. Multi-Level Hierarchical Subtotals via ROLLUP
-- Generates aggregations for:
--   Level 1: (Region, Year, Land Cover)
--   Level 2: (Region, Year, ALL Land Covers)
--   Level 3: (Region, ALL Years, ALL Land Covers)
--   Level 4: (Grand Total across all regions and periods)
-- -----------------------------------------------------------------------------
SELECT 
    COALESCE(dr.name, '--- ALL REGIONS (Grand Total) ---') AS region_name,
    COALESCE(dd.year::text, '--- ALL YEARS ---') AS observation_year,
    COALESCE(dlc.name, '--- ALL LAND COVERS ---') AS land_cover,
    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_area_sq_km,
    ROUND(AVG(fo.area) / 1000000.0, 2) AS avg_area_sq_km,
    SUM(fo.observation_count) AS total_observations
FROM warehouse.fact_observation fo
JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
WHERE dr.name IN ('Delhi NCR', 'Mumbai Metropolitan')
GROUP BY ROLLUP (dr.name, dd.year, dlc.name)
ORDER BY dr.name, dd.year NULLS LAST, dlc.name NULLS LAST;


-- -----------------------------------------------------------------------------
-- 2. Multi-Dimensional Cross-Tabulation via CUBE
-- Generates all $2^N$ combinations of grouping columns across Satellite Operator & Sensor Type
-- -----------------------------------------------------------------------------
SELECT 
    COALESCE(ds.operator, 'ALL OPERATORS') AS space_agency,
    COALESCE(dse.sensor_type, 'ALL SENSOR TYPES') AS sensor_technology,
    COUNT(DISTINCT fo.date_key) AS active_acquisition_days,
    COUNT(fo.observation_fact_key) AS total_fact_rows,
    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_area_measured_sq_km
FROM warehouse.fact_observation fo
JOIN warehouse.dim_satellite ds ON fo.satellite_key = ds.satellite_key
JOIN warehouse.dim_sensor dse ON fo.sensor_key = dse.sensor_key
GROUP BY CUBE (ds.operator, dse.sensor_type)
ORDER BY ds.operator NULLS LAST, dse.sensor_type NULLS LAST;


-- -----------------------------------------------------------------------------
-- 3. Targeted Aggregations using GROUPING SETS
-- Computes specific slice aggregations without calculating the entire power set
-- -----------------------------------------------------------------------------
SELECT 
    dr.name AS region_name,
    dd.year AS observation_year,
    dlc.name AS land_cover,
    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_sq_km
FROM warehouse.fact_observation fo
JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
WHERE dlc.name IN ('Urban', 'Forest')
GROUP BY GROUPING SETS (
    (dr.name, dd.year, dlc.name), -- Regional yearly breakdown
    (dr.name, dlc.name),          -- Regional totals by category
    (dlc.name)                    -- Global land cover totals
)
ORDER BY dr.name NULLS LAST, dd.year NULLS LAST, dlc.name;


-- -----------------------------------------------------------------------------
-- 4. Materialized View Instant Lookup vs Fact Table Scan Benchmark
-- Compares execution runtime between scanning fact rows vs indexed Materialized View
-- -----------------------------------------------------------------------------
-- Scan over fact table:
EXPLAIN ANALYZE
SELECT 
    dr.name, dd.year, dd.quarter, dlc.name,
    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_area_sq_km
FROM warehouse.fact_observation fo
JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
WHERE dr.region_key = 1 AND dd.year = 2023 AND dd.quarter = 1
GROUP BY dr.name, dd.year, dd.quarter, dlc.name;

-- Direct Materialized View index seek:
EXPLAIN ANALYZE
SELECT region_name, year, quarter, land_cover_name, total_area_sq_km
FROM warehouse.mvw_regional_quarterly_landcover
WHERE region_key = 1 AND year = 2023 AND quarter = 1;
