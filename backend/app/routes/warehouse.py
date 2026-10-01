from fastapi import APIRouter, HTTPException, Query
from app.database import get_db

router = APIRouter(prefix="/warehouse", tags=["Data Warehouse & OLAP"])


@router.get("/quarterly-trends")
def get_quarterly_trends(region_id: int = None):
    """Retrieves quarterly land cover distribution from the Materialized View."""
    try:
        with get_db() as cur:
            query = """
                SELECT 
                    region_key,
                    region_name,
                    region_type,
                    year,
                    quarter,
                    (year || '-Q' || quarter) AS period_label,
                    land_cover_key,
                    land_cover_name,
                    total_area_sq_km,
                    avg_area_sq_km,
                    total_observations
                FROM warehouse.mvw_regional_quarterly_landcover
            """
            params = []
            if region_id:
                query += " WHERE region_key = %s "
                params.append(region_id)
            query += " ORDER BY region_name, year, quarter, land_cover_name;"

            cur.execute(query, tuple(params))
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/urban-expansion")
def get_urban_expansion():
    """Calculates rolling 3-quarter window and growth metrics for Urban land cover."""
    try:
        with get_db() as cur:
            cur.execute("""
                WITH quarterly_urban AS (
                    SELECT 
                        dr.name AS region_name,
                        dd.year,
                        dd.quarter,
                        (dd.year || '-Q' || dd.quarter) AS period,
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
                    period,
                    urban_sq_km,
                    ROUND(
                        AVG(urban_sq_km) OVER (
                            PARTITION BY region_name 
                            ORDER BY year, quarter 
                            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                        ), 2
                    ) AS rolling_3q_avg_sq_km,
                    ROUND(
                        urban_sq_km - LAG(urban_sq_km) OVER (
                            PARTITION BY region_name ORDER BY year, quarter
                        ), 2
                    ) AS quarterly_delta_sq_km
                FROM quarterly_urban
                WHERE region_name IN ('Delhi NCR', 'Mumbai Metropolitan', 'Bengaluru Urban')
                ORDER BY region_name, year, quarter;
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sensor-metrics")
def get_sensor_metrics():
    """Evaluates observation load, area captured, and resolution across sensors."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT 
                    ds.name AS satellite_name,
                    dse.name AS sensor_name,
                    dse.sensor_type,
                    dse.resolution AS resolution_meters,
                    COUNT(DISTINCT fo.date_key) AS active_dates,
                    COUNT(fo.observation_fact_key) AS fact_records,
                    ROUND(SUM(fo.area) / 1000000.0, 2) AS total_area_sq_km
                FROM warehouse.fact_observation fo
                JOIN warehouse.dim_satellite ds ON fo.satellite_key = ds.satellite_key
                JOIN warehouse.dim_sensor dse ON fo.sensor_key = dse.sensor_key
                GROUP BY ds.name, dse.name, dse.sensor_type, dse.resolution
                ORDER BY total_area_sq_km DESC;
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deforestation-index")
def get_deforestation_index():
    """Tracks Forest loss and changes year-over-year using Window Functions."""
    try:
        with get_db() as cur:
            cur.execute("""
                WITH annual_forest AS (
                    SELECT 
                        dr.name AS region_name,
                        dd.year,
                        ROUND(AVG(fo.area) / 1000000.0, 2) AS forest_sq_km
                    FROM warehouse.fact_observation fo
                    JOIN warehouse.dim_region dr ON fo.region_key = dr.region_key
                    JOIN warehouse.dim_date dd ON fo.date_key = dd.date_key
                    JOIN warehouse.dim_land_cover dlc ON fo.land_cover_key = dlc.land_cover_key
                    WHERE dlc.name = 'Forest'
                    GROUP BY dr.name, dd.year
                )
                SELECT 
                    region_name,
                    year,
                    forest_sq_km,
                    LAG(forest_sq_km) OVER (PARTITION BY region_name ORDER BY year) AS prev_year_forest_sq_km,
                    ROUND(forest_sq_km - LAG(forest_sq_km) OVER (PARTITION BY region_name ORDER BY year), 2) AS annual_loss_sq_km,
                    ROUND((forest_sq_km - LAG(forest_sq_km) OVER (PARTITION BY region_name ORDER BY year)) / 
                          NULLIF(LAG(forest_sq_km) OVER (PARTITION BY region_name ORDER BY year), 0) * 100.0, 2) AS loss_pct
                FROM annual_forest
                ORDER BY region_name, year;
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
