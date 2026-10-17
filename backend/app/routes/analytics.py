import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.database import get_db

router = APIRouter(tags=["Prompt Analytical Endpoints"])


@router.get("/dashboard/summary")
def get_dashboard_summary():
    """Summary metrics across operational (3NF) and data warehouse (Star Schema)."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM operational.satellite) AS total_satellites,
                    (SELECT COUNT(*) FROM operational.sensor) AS total_sensors,
                    (SELECT COUNT(*) FROM operational.region) AS total_regions,
                    (SELECT COUNT(*) FROM operational.observation) AS total_observations,
                    (SELECT COUNT(*) FROM operational.change_event) AS total_change_events,
                    (SELECT COUNT(*) FROM warehouse.fact_observation) AS total_fact_rows,
                    (SELECT COUNT(*) FROM warehouse.dim_date) AS total_dim_dates,
                    (SELECT ROUND(SUM(changed_area) / 1000000.0, 2) FROM operational.change_event) AS total_changed_area_sq_km,
                    (SELECT pg_size_pretty(pg_database_size('satellite_db'))) AS database_size;
            """)
            row = cur.fetchone()
            return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/satellites")
def list_satellites():
    """Retrieves all satellites with associated sensor counts and mission status."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT 
                    s.satellite_id,
                    s.name,
                    s.operator,
                    s.launch_date,
                    s.status,
                    COUNT(se.sensor_id) AS sensor_count
                FROM operational.satellite s
                LEFT JOIN operational.sensor se ON s.satellite_id = se.satellite_id
                GROUP BY s.satellite_id, s.name, s.operator, s.launch_date, s.status
                ORDER BY s.satellite_id;
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sensors")
def list_sensors():
    """Retrieves all sensors with host satellite info and ground resolution."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT 
                    se.sensor_id,
                    se.name AS sensor_name,
                    se.sensor_type,
                    se.resolution,
                    s.satellite_id,
                    s.name AS satellite_name,
                    (SELECT COUNT(*) FROM operational.observation o WHERE o.sensor_id = se.sensor_id) AS observation_count
                FROM operational.sensor se
                JOIN operational.satellite s ON se.satellite_id = s.satellite_id
                ORDER BY se.sensor_id;
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regions")
def list_regions():
    """Retrieves monitored regions with PostGIS metric area and spatial geometry."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT 
                    r.region_id,
                    r.name,
                    r.region_type,
                    ROUND((ST_Area(r.boundary::geography) / 1000000.0)::numeric, 2) AS area_sq_km,
                    ST_AsGeoJSON(r.boundary) AS geojson,
                    (SELECT COUNT(*) FROM operational.observation o WHERE o.region_id = r.region_id) AS observation_count,
                    (SELECT COUNT(*) FROM operational.change_event ce WHERE ce.region_id = r.region_id) AS change_events_count
                FROM operational.region r
                ORDER BY r.region_id;
            """)
            rows = cur.fetchall()
            for r in rows:
                if "geojson" in r and r["geojson"]:
                    r["geometry"] = json.loads(r["geojson"])
            return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/observations")
def list_observations(
    region_id: Optional[int] = None,
    sensor_id: Optional[int] = None,
    limit: int = Query(100, le=500)
):
    """Retrieves observations with satellite, sensor, and region details."""
    try:
        with get_db() as cur:
            query = """
                SELECT 
                    o.observation_id,
                    o.observation_date,
                    o.image_reference,
                    r.region_id,
                    r.name AS region_name,
                    r.region_type,
                    s.name AS satellite_name,
                    se.sensor_id,
                    se.name AS sensor_name,
                    se.sensor_type,
                    se.resolution
                FROM operational.observation o
                JOIN operational.region r ON o.region_id = r.region_id
                JOIN operational.sensor se ON o.sensor_id = se.sensor_id
                JOIN operational.satellite s ON se.satellite_id = s.satellite_id
                WHERE 1=1
            """
            params = []
            if region_id:
                query += " AND o.region_id = %s "
                params.append(region_id)
            if sensor_id:
                query += " AND o.sensor_id = %s "
                params.append(sensor_id)

            query += " ORDER BY o.observation_date DESC LIMIT %s;"
            params.append(limit)

            cur.execute(query, tuple(params))
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/land-cover/trends")
def get_land_cover_trends(region_id: Optional[int] = None):
    """Retrieves analytical land-cover time-series trends from warehouse star schema."""
    try:
        with get_db() as cur:
            query = """
                SELECT 
                    dr.region_id,
                    dr.name AS region_name,
                    dr.region_type,
                    dd.year,
                    dd.quarter,
                    (dd.year || '-Q' || dd.quarter) AS period,
                    dlc.name AS land_cover_name,
                    ROUND(SUM(fo.area) / 1000000.0, 2) AS area_sq_km,
                    SUM(fo.observation_count) AS observations
                FROM warehouse.fact_observation fo
                JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
                JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
                JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
                WHERE 1=1
            """
            params = []
            if region_id:
                query += " AND dr.region_id = %s "
                params.append(region_id)

            query += """
                GROUP BY dr.region_id, dr.name, dr.region_type, dd.year, dd.quarter, dlc.name
                ORDER BY dr.name, dd.year, dd.quarter, dlc.name;
            """
            cur.execute(query, tuple(params))
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/changes")
def list_changes(region_id: Optional[int] = None):
    """Retrieves detected change events log with transition areas."""
    try:
        with get_db() as cur:
            query = """
                SELECT 
                    change_id,
                    region_id,
                    region_name,
                    region_type,
                    from_land_cover,
                    to_land_cover,
                    start_date,
                    end_date,
                    duration_days,
                    changed_area_sq_km
                FROM operational.vw_change_event_details
            """
            params = []
            if region_id:
                query += " WHERE region_id = %s "
                params.append(region_id)
            query += " ORDER BY changed_area_sq_km DESC;"

            cur.execute(query, tuple(params))
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/satellites")
def get_analytics_satellites():
    """Observation volume, operational period, and sensor count per satellite."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT 
                    ds.satellite_id,
                    ds.name AS satellite_name,
                    ds.operator,
                    ds.status,
                    COUNT(DISTINCT fo.sensor_key) AS sensor_count,
                    COUNT(DISTINCT fo.date_key) AS active_observation_days,
                    COUNT(fo.observation_fact_key) AS fact_observations_count,
                    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_area_covered_sq_km
                FROM warehouse.fact_observation fo
                JOIN warehouse.dim_satellite ds ON fo.satellite_key = ds.satellite_key
                GROUP BY ds.satellite_id, ds.name, ds.operator, ds.status
                ORDER BY fact_observations_count DESC;
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/sensors")
def get_analytics_sensors():
    """Observation performance and coverage analytics grouped by sensor."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT 
                    dse.sensor_id,
                    dse.name AS sensor_name,
                    dse.sensor_type,
                    dse.resolution AS resolution_meters,
                    ds.name AS satellite_name,
                    COUNT(fo.observation_fact_key) AS fact_records,
                    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_coverage_sq_km
                FROM warehouse.fact_observation fo
                JOIN warehouse.dim_sensor dse ON fo.sensor_key = dse.sensor_key
                JOIN warehouse.dim_satellite ds ON fo.satellite_key = ds.satellite_key
                GROUP BY dse.sensor_id, dse.name, dse.sensor_type, dse.resolution, ds.name
                ORDER BY total_coverage_sq_km DESC;
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/regions")
def get_analytics_regions():
    """Observation density, physical metric area, and change count per region."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT 
                    dr.region_id,
                    dr.name AS region_name,
                    dr.region_type,
                    ROUND((ST_Area(r.boundary::geography) / 1000000.0)::numeric, 2) AS geographic_area_sq_km,
                    COUNT(DISTINCT fo.date_key) AS observation_dates_count,
                    COUNT(fo.observation_fact_key) AS fact_rows_count,
                    (SELECT COUNT(*) FROM operational.change_event ce WHERE ce.region_id = dr.region_id) AS change_events_count,
                    (SELECT ROUND(COALESCE(SUM(ce.changed_area), 0) / 1000000.0, 2) FROM operational.change_event ce WHERE ce.region_id = dr.region_id) AS shifted_area_sq_km
                FROM warehouse.dim_region dr
                JOIN operational.region r ON dr.region_id = r.region_id
                LEFT JOIN warehouse.fact_observation fo ON dr.region_key = fo.region_key
                GROUP BY dr.region_id, dr.name, dr.region_type, r.boundary
                ORDER BY dr.region_id;
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/geospatial/observations")
def get_geospatial_observations(region_id: Optional[int] = None, limit: int = 50):
    """GeoJSON FeatureCollection of satellite observation footprint polygons."""
    try:
        with get_db() as cur:
            query = """
                SELECT 
                    o.observation_id,
                    o.observation_date,
                    o.image_reference,
                    r.name AS region_name,
                    s.name AS satellite_name,
                    se.name AS sensor_name,
                    se.sensor_type,
                    se.resolution,
                    ST_AsGeoJSON(o.footprint) AS geojson_geom
                FROM operational.observation o
                JOIN operational.region r ON o.region_id = r.region_id
                JOIN operational.sensor se ON o.sensor_id = se.sensor_id
                JOIN operational.satellite s ON se.satellite_id = s.satellite_id
                WHERE 1=1
            """
            params = []
            if region_id:
                query += " AND o.region_id = %s "
                params.append(region_id)

            query += " ORDER BY o.observation_date DESC LIMIT %s;"
            params.append(limit)

            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            features = []
            for r in rows:
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(r["geojson_geom"]),
                    "properties": {
                        "observation_id": r["observation_id"],
                        "observation_date": str(r["observation_date"]),
                        "image_reference": r["image_reference"],
                        "region_name": r["region_name"],
                        "satellite_name": r["satellite_name"],
                        "sensor_name": r["sensor_name"],
                        "sensor_type": r["sensor_type"],
                        "resolution": float(r["resolution"])
                    }
                })

            return {
                "type": "FeatureCollection",
                "features": features
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regions/{region_id}/analysis")
def get_region_deep_analysis(region_id: int):
    """Comprehensive analytical profile: geography, land cover history, and detected changes."""
    try:
        with get_db() as cur:
            # Region profile
            cur.execute("""
                SELECT 
                    r.region_id,
                    r.name,
                    r.region_type,
                    ROUND((ST_Area(r.boundary::geography) / 1000000.0)::numeric, 2) AS area_sq_km,
                    ST_AsGeoJSON(r.boundary) AS geojson,
                    ST_Y(ST_Centroid(r.boundary)) AS centroid_lat,
                    ST_X(ST_Centroid(r.boundary)) AS centroid_lng
                FROM operational.region r
                WHERE r.region_id = %s;
            """, (region_id,))
            region = cur.fetchone()
            if not region:
                raise HTTPException(status_code=404, detail="Region not found")

            # Land cover trend over time
            cur.execute("""
                SELECT 
                    dd.year,
                    dd.quarter,
                    (dd.year || '-Q' || dd.quarter) AS period,
                    dlc.name AS land_cover,
                    ROUND(SUM(fo.area) / 1000000.0, 2) AS area_sq_km
                FROM warehouse.fact_observation fo
                JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
                JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
                JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
                WHERE dr.region_id = %s
                GROUP BY dd.year, dd.quarter, dlc.name
                ORDER BY dd.year, dd.quarter, dlc.name;
            """, (region_id,))
            trends = cur.fetchall()

            # Changes in this region
            cur.execute("""
                SELECT 
                    change_id,
                    from_land_cover,
                    to_land_cover,
                    start_date,
                    end_date,
                    duration_days,
                    changed_area_sq_km
                FROM operational.vw_change_event_details
                WHERE region_id = %s
                ORDER BY changed_area_sq_km DESC;
            """, (region_id,))
            changes = cur.fetchall()

            # Observations summary
            cur.execute("""
                SELECT 
                    COUNT(*) AS total_observations,
                    MIN(observation_date) AS earliest_observation,
                    MAX(observation_date) AS latest_observation
                FROM operational.observation
                WHERE region_id = %s;
            """, (region_id,))
            obs_stats = cur.fetchone()

            result = dict(region)
            if "geojson" in result and result["geojson"]:
                result["geometry"] = json.loads(result["geojson"])
            result["trends"] = [dict(t) for t in trends]
            result["changes"] = [dict(c) for c in changes]
            result["observation_stats"] = dict(obs_stats)
            return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
