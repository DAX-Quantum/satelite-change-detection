-- =========================================================
-- 03_views_and_procedures.sql
-- Database Views, Materialized Views, and Stored Functions
-- Supports Fast Analytics, Dashboard Integration, and Viva Demonstrations
-- =========================================================

-- ---------------------------------------------------------
-- VIEW 1: Operational Change Events with Full Metadata
-- Joins change_event with region and land cover names
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW operational.vw_change_event_details AS
SELECT 
    ce.change_id,
    r.region_id,
    r.name AS region_name,
    r.region_type,
    lc1.name AS from_land_cover,
    lc2.name AS to_land_cover,
    ce.start_date,
    ce.end_date,
    (ce.end_date - ce.start_date) AS duration_days,
    ROUND((ce.changed_area / 1000000.0)::numeric, 2) AS changed_area_sq_km,
    ST_AsGeoJSON(r.boundary) AS region_geojson
FROM operational.change_event ce
JOIN operational.region r ON ce.region_id = r.region_id
JOIN operational.land_cover lc1 ON ce.from_land_cover_id = lc1.land_cover_id
JOIN operational.land_cover lc2 ON ce.to_land_cover_id = lc2.land_cover_id;


-- ---------------------------------------------------------
-- MATERIALIZED VIEW 2: Warehouse Regional Land Cover Quarterly Aggregates
-- Materialized view for fast dashboard analytics without scanning fact rows
-- ---------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS warehouse.mvw_regional_quarterly_landcover CASCADE;

CREATE MATERIALIZED VIEW warehouse.mvw_regional_quarterly_landcover AS
SELECT 
    dr.region_key,
    dr.name AS region_name,
    dr.region_type,
    dd.year,
    dd.quarter,
    dlc.land_cover_key,
    dlc.name AS land_cover_name,
    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_area_sq_km,
    ROUND(AVG(fo.area) / 1000000.0, 2) AS avg_area_sq_km,
    SUM(fo.observation_count) AS total_observations
FROM warehouse.fact_observation fo
JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
GROUP BY 
    dr.region_key, dr.name, dr.region_type,
    dd.year, dd.quarter,
    dlc.land_cover_key, dlc.name
WITH DATA;

CREATE UNIQUE INDEX idx_mvw_region_quarter_lc 
ON warehouse.mvw_regional_quarterly_landcover (region_key, year, quarter, land_cover_key);


-- ---------------------------------------------------------
-- STORED FUNCTION 1: Compare Land Cover Shift Between Two Dates
-- Given a region_id and two observation dates, calculates net shift for all land covers
-- ---------------------------------------------------------
CREATE OR REPLACE FUNCTION operational.fn_compare_landcover(
    p_region_id INTEGER,
    p_date_start DATE,
    p_date_end DATE
)
RETURNS TABLE (
    land_cover_name VARCHAR(50),
    initial_area_sq_km NUMERIC,
    final_area_sq_km NUMERIC,
    net_change_sq_km NUMERIC,
    change_pct NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH start_obs AS (
        SELECT olc.land_cover_id, SUM(olc.area) AS start_area
        FROM operational.observation o
        JOIN operational.observation_land_cover olc ON o.observation_id = olc.observation_id
        WHERE o.region_id = p_region_id AND o.observation_date = p_date_start
        GROUP BY olc.land_cover_id
    ),
    end_obs AS (
        SELECT olc.land_cover_id, SUM(olc.area) AS end_area
        FROM operational.observation o
        JOIN operational.observation_land_cover olc ON o.observation_id = olc.observation_id
        WHERE o.region_id = p_region_id AND o.observation_date = p_date_end
        GROUP BY olc.land_cover_id
    )
    SELECT 
        lc.name,
        ROUND((COALESCE(s.start_area, 0) / 1000000.0)::numeric, 2) AS initial_area_sq_km,
        ROUND((COALESCE(e.end_area, 0) / 1000000.0)::numeric, 2) AS final_area_sq_km,
        ROUND(((COALESCE(e.end_area, 0) - COALESCE(s.start_area, 0)) / 1000000.0)::numeric, 2) AS net_change_sq_km,
        ROUND(
            ((COALESCE(e.end_area, 0) - COALESCE(s.start_area, 0)) / 
             NULLIF(COALESCE(s.start_area, 0), 0) * 100.0)::numeric, 
            2
        ) AS change_pct
    FROM operational.land_cover lc
    LEFT JOIN start_obs s ON lc.land_cover_id = s.land_cover_id
    LEFT JOIN end_obs e ON lc.land_cover_id = e.land_cover_id
    ORDER BY net_change_sq_km DESC;
END;
$$ LANGUAGE plpgsql;


-- ---------------------------------------------------------
-- TRIGGER: Audit Log on Change Events
-- Demonstrates Triggers & Procedures in DBMS
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS operational.change_event_audit (
    audit_id SERIAL PRIMARY KEY,
    action_type VARCHAR(10) NOT NULL,
    change_id INTEGER,
    region_id INTEGER,
    changed_area NUMERIC(14,2),
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION operational.trg_audit_change_event()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO operational.change_event_audit (action_type, change_id, region_id, changed_area)
        VALUES ('INSERT', NEW.change_id, NEW.region_id, NEW.changed_area);
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO operational.change_event_audit (action_type, change_id, region_id, changed_area)
        VALUES ('UPDATE', NEW.change_id, NEW.region_id, NEW.changed_area);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_change_event ON operational.change_event;
CREATE TRIGGER trg_audit_change_event
AFTER INSERT OR UPDATE ON operational.change_event
FOR EACH ROW EXECUTE FUNCTION operational.trg_audit_change_event();
