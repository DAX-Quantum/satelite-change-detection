-- =========================================================
-- 02_olap_queries.sql
-- Star Schema OLAP & Dimensional Analysis Queries (Warehouse Schema)
-- Demonstrating ROLLUP, Window Functions, and Temporal Aggregations
-- =========================================================

SET search_path TO warehouse, public;

-- ---------------------------------------------------------
-- OLAP 1: Regional Land-Cover Composition with Multi-Level ROLLUP
-- Calculates Subtotals at (Region, Year), (Region), and Grand Total
-- ---------------------------------------------------------
SELECT 
    COALESCE(dr.name, '--- ALL REGIONS ---') AS region_name,
    COALESCE(dd.year::text, '--- ALL YEARS ---') AS observation_year,
    COALESCE(dlc.name, '--- ALL LAND COVERS ---') AS land_cover,
    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_area_sq_km,
    SUM(fo.observation_count) AS total_observations
FROM warehouse.fact_observation fo
JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
WHERE dr.name IN ('Delhi NCR', 'Central India Forest Belt (Synthetic)')
GROUP BY ROLLUP (dr.name, dd.year, dlc.name)
ORDER BY dr.name, dd.year NULLS LAST, dlc.name NULLS LAST;


-- ---------------------------------------------------------
-- OLAP 2: Year-over-Year Land Cover Dynamics (Window Function LAG)
-- Tracks shifts in Forest and Urban area year-over-year
-- ---------------------------------------------------------
WITH yearly_metrics AS (
    SELECT 
        dr.name AS region_name,
        dlc.name AS land_cover,
        dd.year,
        ROUND(AVG(fo.area) / 1000000.0, 2) AS avg_area_sq_km
    FROM warehouse.fact_observation fo
    JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
    JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
    JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
    GROUP BY dr.name, dlc.name, dd.year
)
SELECT 
    region_name,
    land_cover,
    year,
    avg_area_sq_km,
    LAG(avg_area_sq_km) OVER (
        PARTITION BY region_name, land_cover ORDER BY year
    ) AS previous_year_area_sq_km,
    ROUND(
        avg_area_sq_km - LAG(avg_area_sq_km) OVER (
            PARTITION BY region_name, land_cover ORDER BY year
        ), 2
    ) AS annual_delta_sq_km,
    ROUND(
        (avg_area_sq_km - LAG(avg_area_sq_km) OVER (
            PARTITION BY region_name, land_cover ORDER BY year
        )) / NULLIF(LAG(avg_area_sq_km) OVER (
            PARTITION BY region_name, land_cover ORDER BY year
        ), 0) * 100.0, 2
    ) AS percentage_change
FROM yearly_metrics
WHERE land_cover IN ('Urban', 'Forest')
ORDER BY region_name, land_cover, year;


-- ---------------------------------------------------------
-- OLAP 3: Satellite & Sensor Efficiency Metrics
-- Identifies observation coverage, total square km captured, and resolution distribution
-- ---------------------------------------------------------
SELECT 
    ds.name AS satellite_name,
    dse.name AS sensor_name,
    dse.sensor_type,
    dse.resolution AS resolution_meters,
    COUNT(DISTINCT fo.date_key) AS active_observation_dates,
    COUNT(fo.observation_fact_key) AS fact_records_count,
    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_area_measured_sq_km
FROM warehouse.fact_observation fo
JOIN warehouse.dim_satellite ds ON fo.satellite_key = ds.satellite_key
JOIN warehouse.dim_sensor dse ON fo.sensor_key = dse.sensor_key
GROUP BY ds.name, dse.name, dse.sensor_type, dse.resolution
ORDER BY total_area_measured_sq_km DESC;


-- ---------------------------------------------------------
-- OLAP 4: Moving Average (3-Quarter Window) for Urban Expansion
-- Uses ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
-- ---------------------------------------------------------
WITH quarterly_urban AS (
    SELECT 
        dr.name AS region_name,
        dd.year,
        dd.quarter,
        ROUND(SUM(fo.area) / 1000000.0, 2) AS urban_sq_km
    FROM warehouse.fact_observation fo
    JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
    JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
    JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
    WHERE dlc.name = 'Urban'
    GROUP BY dr.name, dd.year, dd.quarter
)
SELECT 
    region_name,
    year,
    quarter,
    urban_sq_km,
    ROUND(
        AVG(urban_sq_km) OVER (
            PARTITION BY region_name 
            ORDER BY year, quarter 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_3q_avg_urban_sq_km
FROM quarterly_urban
WHERE region_name IN ('Delhi NCR', 'Mumbai Metropolitan', 'Bengaluru Urban')
ORDER BY region_name, year, quarter;
