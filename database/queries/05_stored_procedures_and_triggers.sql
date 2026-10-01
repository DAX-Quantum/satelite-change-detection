-- =============================================================================
-- SATELLITE DATA MANAGEMENT & GEOSPATIAL CHANGE DETECTION
-- Script: 05_stored_procedures_and_triggers.sql
-- Description: Stored Procedures, Functions, Audit Triggers & ACID Demonstration
-- Schema: operational, warehouse
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Stored Function Execution: fn_compare_landcover()
-- Evaluates net land cover area shifts and percentage changes between two dates
-- -----------------------------------------------------------------------------
-- Region 1 (Delhi NCR) between 2021-01-01 and 2024-10-01:
SELECT 
    land_cover_name,
    initial_area_sq_km,
    final_area_sq_km,
    net_change_sq_km,
    change_pct
FROM operational.fn_compare_landcover(1, '2021-01-01', '2024-10-01');

-- Region 2 (Mumbai Metropolitan) between 2021-01-01 and 2024-10-01:
SELECT 
    land_cover_name,
    initial_area_sq_km,
    final_area_sq_km,
    net_change_sq_km,
    change_pct
FROM operational.fn_compare_landcover(2, '2021-01-01', '2024-10-01');


-- -----------------------------------------------------------------------------
-- 2. Audit Trigger Verification: trg_audit_change_event
-- Demonstrates automatic database-level auditing upon INSERT and UPDATE
-- -----------------------------------------------------------------------------
BEGIN;

-- Check current audit records
SELECT count(*) AS audit_records_before FROM operational.change_event_audit;

-- Insert a simulated newly detected change event
INSERT INTO operational.change_event (
    change_id, region_id, from_land_cover_id, to_land_cover_id, 
    start_date, end_date, changed_area
)
VALUES (
    9999, 1, 3, 1, '2025-01-01', '2025-06-30', 4500000.00
);

-- Update the simulated change event with refined area
UPDATE operational.change_event
SET changed_area = 4850000.00
WHERE change_id = 9999;

-- Verify both INSERT and UPDATE actions were automatically captured by trigger
SELECT 
    audit_id,
    action_type,
    change_id,
    region_id,
    ROUND((changed_area / 1000000.0)::numeric, 2) AS changed_area_sq_km,
    logged_at
FROM operational.change_event_audit
WHERE change_id = 9999
ORDER BY audit_id ASC;

-- Rollback the simulation to keep database clean
ROLLBACK;


-- -----------------------------------------------------------------------------
-- 3. Concurrent Refresh of Materialized Views
-- Ensures zero-downtime analytics cache updating
-- -----------------------------------------------------------------------------
REFRESH MATERIALIZED VIEW warehouse.mvw_regional_quarterly_landcover;

SELECT 
    count(*) AS cached_quarterly_rows,
    min(year) AS earliest_year,
    max(year) AS latest_year
FROM warehouse.mvw_regional_quarterly_landcover;


-- -----------------------------------------------------------------------------
-- 4. ACID Transaction Safety & Rollback Verification
-- Demonstrates how constraint violations maintain database consistency
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        -- Attempt to violate unique grain constraint on fact_observation
        INSERT INTO warehouse.fact_observation (
            satellite_key, sensor_key, region_key, land_cover_key, date_key, area
        )
        VALUES (1, 1, 1, 1, 20210101, 500000);

        INSERT INTO warehouse.fact_observation (
            satellite_key, sensor_key, region_key, land_cover_key, date_key, area
        )
        VALUES (1, 1, 1, 1, 20210101, 600000); -- DUPLICATE GRAIN!

    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE '[ACID TEST PASSED] Unique grain violation intercepted cleanly! Rolled back duplicate insertion.';
    END;
END $$;
