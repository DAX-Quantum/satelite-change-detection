-- =============================================================================
-- SATELLITE DATA MANAGEMENT & GEOSPATIAL CHANGE DETECTION
-- Script: 04_advanced_window_functions.sql
-- Description: Advanced SQL Window Functions (LAG, LEAD, Moving Averages, Ranking)
-- Schema: warehouse, operational
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Year-over-Year Land Cover Shifts using LAG()
-- Calculates annual net delta (sq km) and growth percentage per category
-- -----------------------------------------------------------------------------
WITH annual_series AS (
    SELECT 
        dr.name AS region_name,
        dlc.name AS land_cover,
        dd.year,
        ROUND(AVG(fo.area) / 1000000.0, 2) AS mean_area_sq_km
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
    mean_area_sq_km,
    LAG(mean_area_sq_km) OVER (
        PARTITION BY region_name, land_cover ORDER BY year
    ) AS prev_year_area_sq_km,
    ROUND(
        mean_area_sq_km - LAG(mean_area_sq_km) OVER (
            PARTITION BY region_name, land_cover ORDER BY year
        ), 2
    ) AS yoy_delta_sq_km,
    ROUND(
        (mean_area_sq_km - LAG(mean_area_sq_km) OVER (
            PARTITION BY region_name, land_cover ORDER BY year
        )) / NULLIF(LAG(mean_area_sq_km) OVER (
            PARTITION BY region_name, land_cover ORDER BY year
        ), 0) * 100.0, 2
    ) AS yoy_growth_pct
FROM annual_series
WHERE land_cover IN ('Urban', 'Forest')
ORDER BY region_name, land_cover, year;


-- -----------------------------------------------------------------------------
-- 2. Rolling 3-Quarter Window Moving Average
-- Smoothes seasonal noise using dynamic sliding frames:
-- ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
-- -----------------------------------------------------------------------------
WITH quarterly_urban AS (
    SELECT 
        dr.name AS region_name,
        dd.year,
        dd.quarter,
        (dd.year || '-Q' || dd.quarter) AS period_label,
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
    period_label,
    urban_sq_km,
    ROUND(
        AVG(urban_sq_km) OVER (
            PARTITION BY region_name 
            ORDER BY year, quarter 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_3q_avg_sq_km,
    ROUND(
        urban_sq_km - AVG(urban_sq_km) OVER (
            PARTITION BY region_name 
            ORDER BY year, quarter 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2
    ) AS divergence_from_trend_sq_km
FROM quarterly_urban
WHERE region_name IN ('Delhi NCR', 'Mumbai Metropolitan', 'Bengaluru Urban')
ORDER BY region_name, period_label;


-- -----------------------------------------------------------------------------
-- 3. Severity Ranking of Detected Land Cover Changes (DENSE_RANK & ROW_NUMBER)
-- Ranks transitions across regions by total affected surface area
-- -----------------------------------------------------------------------------
SELECT 
    ce.change_id,
    r.name AS region_name,
    lc1.name AS from_cover,
    lc2.name AS to_cover,
    ce.start_date,
    ce.end_date,
    ROUND((ce.changed_area / 1000000.0)::numeric, 2) AS shifted_area_sq_km,
    ROW_NUMBER() OVER (
        PARTITION BY r.name ORDER BY ce.changed_area DESC
    ) AS regional_rank,
    DENSE_RANK() OVER (
        ORDER BY ce.changed_area DESC
    ) AS national_severity_rank
FROM operational.change_event ce
JOIN operational.region r ON ce.region_id = r.region_id
JOIN operational.land_cover lc1 ON ce.from_land_cover_id = lc1.land_cover_id
JOIN operational.land_cover lc2 ON ce.to_land_cover_id = lc2.land_cover_id
ORDER BY national_severity_rank ASC
LIMIT 12;


-- -----------------------------------------------------------------------------
-- 4. Cumulative Running Total of Measured Surface Area
-- Uses unbounded preceding window frame to compute accumulated sensor intake
-- -----------------------------------------------------------------------------
SELECT 
    dd.year,
    dd.month,
    dd.month_name,
    ROUND(SUM(fo.area) / 1000000.0, 2) AS monthly_area_sq_km,
    ROUND(
        SUM(SUM(fo.area) / 1000000.0) OVER (
            PARTITION BY dd.year 
            ORDER BY dd.month 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 2
    ) AS ytd_cumulative_area_sq_km
FROM warehouse.fact_observation fo
JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
GROUP BY dd.year, dd.month, dd.month_name
ORDER BY dd.year, dd.month;
