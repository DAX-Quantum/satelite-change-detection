from fastapi import APIRouter, HTTPException
from app.database import get_db

router = APIRouter(prefix="/stats", tags=["System Statistics"])


@router.get("/overview")
def get_system_overview():
    """Returns top-level summary metrics across operational and warehouse schemas."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM operational.satellite) AS satellites_count,
                    (SELECT COUNT(*) FROM operational.sensor) AS sensors_count,
                    (SELECT COUNT(*) FROM operational.region) AS regions_count,
                    (SELECT COUNT(*) FROM operational.observation) AS observations_count,
                    (SELECT COUNT(*) FROM operational.change_event) AS change_events_count,
                    (SELECT COUNT(*) FROM warehouse.dim_date) AS dim_dates_count,
                    (SELECT COUNT(*) FROM warehouse.fact_observation) AS fact_observations_count,
                    (SELECT COUNT(*) FROM operational.image_data) AS images_count,
                    (SELECT ROUND(SUM(changed_area) / 1000000.0, 2) FROM operational.change_event) AS total_changed_area_sq_km,
                    (SELECT pg_size_pretty(pg_database_size('satellite_db'))) AS database_size;
            """)
            row = cur.fetchone()
            return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schemas")
def get_schema_tables():
    """Returns table listing with row counts and column definitions for the architecture viewer."""
    try:
        with get_db() as cur:
            cur.execute("""
                SELECT 
                    table_schema,
                    table_name,
                    (
                        SELECT count(*) 
                        FROM information_schema.columns c 
                        WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name
                    ) AS column_count
                FROM information_schema.tables t
                WHERE table_schema IN ('operational', 'warehouse')
                  AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name;
            """)
            tables = cur.fetchall()

            # For each table, get live row count
            results = []
            for t in tables:
                schema = t["table_schema"]
                name = t["table_name"]
                cur.execute(f"SELECT COUNT(*) FROM {schema}.{name};")
                count = cur.fetchone()["count"]
                
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position;
                """, (schema, name))
                columns = cur.fetchall()

                results.append({
                    "schema": schema,
                    "table_name": name,
                    "row_count": count,
                    "columns": [dict(c) for c in columns]
                })

            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
