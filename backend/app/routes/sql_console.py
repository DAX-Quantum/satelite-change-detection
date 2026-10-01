import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import get_db

router = APIRouter(prefix="/sql", tags=["SQL & Viva Console"])


class QueryRequest(BaseModel):
    query: str
    explain: bool = False


VIVA_PRESET_QUERIES = [
    {
        "id": "q1_spatial_overlap",
        "title": "PostGIS Spatial Intersection & Coverage %",
        "category": "Spatial (PostGIS)",
        "description": "Calculates exact geometric overlap (sq km) and coverage % between satellite footprints and region boundaries using ST_Intersection and ST_Area.",
        "sql": """SELECT 
    r.name AS region_name,
    r.region_type,
    s.name AS satellite_name,
    o.observation_date,
    ROUND((ST_Area(ST_Intersection(r.boundary, o.footprint)::geography) / 1000000.0)::numeric, 2) AS covered_area_sq_km,
    ROUND((ST_Area(r.boundary::geography) / 1000000.0)::numeric, 2) AS total_region_area_sq_km,
    ROUND((ST_Area(ST_Intersection(r.boundary, o.footprint)::geography) / NULLIF(ST_Area(r.boundary::geography), 0) * 100.0)::numeric, 1) AS coverage_pct
FROM operational.observation o
JOIN operational.region r ON o.region_id = r.region_id
JOIN operational.sensor se ON o.sensor_id = se.sensor_id
JOIN operational.satellite s ON se.satellite_id = s.satellite_id
WHERE ST_Intersects(r.boundary, o.footprint)
ORDER BY coverage_pct DESC
LIMIT 10;"""
    },
    {
        "id": "q2_olap_rollup",
        "title": "Star Schema Hierarchical ROLLUP Subtotals",
        "category": "Data Warehouse (OLAP)",
        "description": "Aggregates land cover area with multi-level subtotals for Region, Year, and Land Cover, ending in Grand Totals.",
        "sql": """SELECT 
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
ORDER BY dr.name, dd.year NULLS LAST, dlc.name NULLS LAST;"""
    },
    {
        "id": "q3_window_lag_yoy",
        "title": "Window Function LAG(): Year-over-Year Shift",
        "category": "SQL Window Functions",
        "description": "Computes annual change deltas and percentage shifts for Urban and Forest areas using LAG() window partition.",
        "sql": """WITH yearly_metrics AS (
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
    LAG(avg_area_sq_km) OVER (PARTITION BY region_name, land_cover ORDER BY year) AS prev_year_sq_km,
    ROUND(avg_area_sq_km - LAG(avg_area_sq_km) OVER (PARTITION BY region_name, land_cover ORDER BY year), 2) AS annual_delta_sq_km,
    ROUND((avg_area_sq_km - LAG(avg_area_sq_km) OVER (PARTITION BY region_name, land_cover ORDER BY year)) / 
          NULLIF(LAG(avg_area_sq_km) OVER (PARTITION BY region_name, land_cover ORDER BY year), 0) * 100.0, 2) AS change_pct
FROM yearly_metrics
WHERE land_cover IN ('Urban', 'Forest')
ORDER BY region_name, land_cover, year;"""
    },
    {
        "id": "q4_rolling_window_avg",
        "title": "Rolling 3-Quarter Window Moving Average",
        "category": "SQL Window Functions",
        "description": "Calculates smoothed 3-quarter moving averages using ROWS BETWEEN 2 PRECEDING AND CURRENT ROW to analyze urban expansion velocity.",
        "sql": """WITH quarterly_urban AS (
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
    ROUND(AVG(urban_sq_km) OVER (
        PARTITION BY region_name 
        ORDER BY year, quarter 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_3q_avg_sq_km
FROM quarterly_urban
WHERE region_name IN ('Delhi NCR', 'Mumbai Metropolitan', 'Bengaluru Urban')
ORDER BY region_name, year, quarter;"""
    },
    {
        "id": "q5_stored_procedure",
        "title": "PL/pgSQL Stored Function: fn_compare_landcover()",
        "category": "Procedures & Triggers",
        "description": "Executes stored function calculating net shift and % change across all land cover categories between two specific observation dates.",
        "sql": """SELECT * FROM operational.fn_compare_landcover(1, '2021-01-01', '2024-10-01');"""
    },
    {
        "id": "q6_geodetic_distances",
        "title": "PostGIS Geodetic Centroid Distances (km)",
        "category": "Spatial (PostGIS)",
        "description": "Uses ST_Centroid and ST_Distance over geography types (WGS84 spheroid) to compute physical distances between monitored regions.",
        "sql": """SELECT 
    r1.name AS region_1,
    r2.name AS region_2,
    ROUND((ST_Distance(ST_Centroid(r1.boundary)::geography, ST_Centroid(r2.boundary)::geography) / 1000.0)::numeric, 2) AS distance_km
FROM operational.region r1
CROSS JOIN operational.region r2
WHERE r1.region_id < r2.region_id
ORDER BY distance_km ASC;"""
    },
    {
        "id": "q7_sensor_efficiency",
        "title": "Satellite & Sensor Observation Volume Analysis",
        "category": "Data Warehouse (OLAP)",
        "description": "Cross-dimensional analysis of total area surveyed, active acquisition dates, and resolution across radar and optical sensors.",
        "sql": """SELECT 
    ds.name AS satellite_name,
    dse.name AS sensor_name,
    dse.sensor_type,
    dse.resolution AS resolution_meters,
    COUNT(DISTINCT fo.date_key) AS active_dates,
    COUNT(fo.observation_fact_key) AS fact_records,
    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_area_measured_sq_km
FROM warehouse.fact_observation fo
JOIN warehouse.dim_satellite ds ON fo.satellite_key = ds.satellite_key
JOIN warehouse.dim_sensor dse ON fo.sensor_key = dse.sensor_key
GROUP BY ds.name, dse.name, dse.sensor_type, dse.resolution
ORDER BY total_area_measured_sq_km DESC;"""
    },
    {
        "id": "q8_change_events_ranking",
        "title": "Ranked Change Events with Duration & Severity",
        "category": "Operational 3NF",
        "description": "Queries the operational view joined with land covers and regions, ranked by total land transition area.",
        "sql": """SELECT 
    change_id,
    region_name,
    region_type,
    from_land_cover,
    to_land_cover,
    start_date,
    end_date,
    duration_days,
    changed_area_sq_km
FROM operational.vw_change_event_details
ORDER BY changed_area_sq_km DESC
LIMIT 10;"""
    }
]


@router.get("/viva-queries")
def get_viva_queries():
    """Returns curated viva demonstration queries."""
    return VIVA_PRESET_QUERIES


@router.post("/execute")
def execute_sql(payload: QueryRequest):
    """Executes read-only SQL queries and returns results with execution latency and plan."""
    cleaned_query = payload.query.strip()
    first_word = cleaned_query.split()[0].upper() if cleaned_query else ""

    forbidden_keywords = ["DROP", "TRUNCATE", "DELETE", "ALTER", "GRANT", "REVOKE"]
    for keyword in forbidden_keywords:
        if keyword in cleaned_query.upper().split():
            raise HTTPException(
                status_code=400,
                detail=f"Query blocked for safety: '{keyword}' statements are disallowed in the interactive console."
            )

    try:
        with get_db() as cur:
            start_time = time.perf_counter()
            cur.execute(cleaned_query)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            rows = cur.fetchall() if cur.description else []
            columns = [desc[0] for desc in cur.description] if cur.description else []

            explain_plan = None
            if payload.explain and first_word in ["SELECT", "WITH"]:
                try:
                    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS) {cleaned_query}")
                    explain_rows = cur.fetchall()
                    explain_plan = [r["QUERY PLAN"] for r in explain_rows if "QUERY PLAN" in r]
                except Exception as ex_err:
                    explain_plan = [f"Could not generate EXPLAIN: {ex_err}"]

            return {
                "success": True,
                "row_count": len(rows),
                "columns": columns,
                "rows": [dict(r) for r in rows],
                "execution_time_ms": round(elapsed_ms, 2),
                "explain_plan": explain_plan
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "execution_time_ms": 0.0
        }
