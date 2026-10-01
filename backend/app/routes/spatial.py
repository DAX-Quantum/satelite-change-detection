import json
from fastapi import APIRouter, HTTPException
from app.database import get_db

router = APIRouter(prefix="/spatial", tags=["Spatial & PostGIS"])


@router.get("/regions")
def get_regions_geojson():
    """Returns regions formatted as a GeoJSON FeatureCollection with attributes."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT 
                    r.region_id,
                    r.name,
                    r.region_type,
                    ROUND((ST_Area(r.boundary::geography) / 1000000.0)::numeric, 2) AS area_sq_km,
                    ST_Y(ST_Centroid(r.boundary)) AS centroid_lat,
                    ST_X(ST_Centroid(r.boundary)) AS centroid_lng,
                    ST_AsGeoJSON(r.boundary) AS geojson_geom,
                    (SELECT COUNT(*) FROM operational.observation o WHERE o.region_id = r.region_id) AS observation_count,
                    (SELECT COUNT(*) FROM operational.change_event ce WHERE ce.region_id = r.region_id) AS change_events_count
                FROM operational.region r
                ORDER BY r.region_id;
            """)
            rows = cur.fetchall()

            features = []
            for r in rows:
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(r["geojson_geom"]),
                    "properties": {
                        "region_id": r["region_id"],
                        "name": r["name"],
                        "region_type": r["region_type"],
                        "area_sq_km": float(r["area_sq_km"]),
                        "centroid": [float(r["centroid_lat"]), float(r["centroid_lng"])],
                        "observation_count": r["observation_count"],
                        "change_events_count": r["change_events_count"],
                    }
                })

            return {
                "type": "FeatureCollection",
                "features": features
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/observations")
def get_observations_geojson(region_id: int = None, limit: int = 50):
    """Returns satellite observation footprints as GeoJSON."""
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
            """
            params = []
            if region_id:
                query += " WHERE o.region_id = %s "
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
                        "resolution_m": float(r["resolution"]) if r["resolution"] else None
                    }
                })

            return {
                "type": "FeatureCollection",
                "features": features
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intersections")
def get_spatial_intersections():
    """Runs a PostGIS spatial intersection query between regions and observation footprints."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT 
                    r.name AS region_name,
                    s.name AS satellite_name,
                    o.observation_date,
                    ROUND((ST_Area(ST_Intersection(r.boundary, o.footprint)::geography) / 1000000.0)::numeric, 2) AS overlap_sq_km,
                    ROUND((ST_Area(r.boundary::geography) / 1000000.0)::numeric, 2) AS total_region_sq_km,
                    ROUND((ST_Area(ST_Intersection(r.boundary, o.footprint)::geography) / NULLIF(ST_Area(r.boundary::geography), 0) * 100.0)::numeric, 1) AS overlap_pct
                FROM operational.observation o
                JOIN operational.region r ON o.region_id = r.region_id
                JOIN operational.sensor se ON o.sensor_id = se.sensor_id
                JOIN operational.satellite s ON se.satellite_id = s.satellite_id
                WHERE ST_Intersects(r.boundary, o.footprint)
                ORDER BY overlap_pct DESC
                LIMIT 15;
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
