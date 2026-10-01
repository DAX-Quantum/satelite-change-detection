"""
stage2_warehouse_load.py

ETL Stage 2: EXTRACT normalized data from the `operational` schema,
TRANSFORM it into dimensional attributes and surrogate key mappings,
and LOAD it into the `warehouse` star schema (dim tables and fact_observation).

Run:
    python etl/scripts/stage2_warehouse_load.py

Prerequisites:
    1. Operational schema loaded (via etl/scripts/stage1_operational_load.py)
    2. Warehouse tables created (via database/warehouse/*.sql)
    3. dim_date pre-populated (covered in 01_dimensions.sql)

This script is idempotent: it preserves dim_date (which is calendar-based),
truncates the fact table and the dimension tables, re-populates the dimensions,
and loads the fact table.
"""

import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "satellite_db"),
    "user": os.getenv("POSTGRES_USER", "satellite_admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "12345"),
}


def truncate_warehouse_tables(cur):
    """Truncates fact and dimension tables (preserving dim_date)."""
    cur.execute("""
        TRUNCATE TABLE
            warehouse.fact_observation,
            warehouse.dim_sensor,
            warehouse.dim_satellite,
            warehouse.dim_region,
            warehouse.dim_land_cover
        RESTART IDENTITY CASCADE;
    """)


def load_dimensions(cur):
    """Extracts from operational schema and loads into warehouse dimension tables."""
    print("Loading dim_satellite...")
    cur.execute("""
        INSERT INTO warehouse.dim_satellite (satellite_id, name, operator, status)
        SELECT satellite_id, name, operator, status
        FROM operational.satellite
        ORDER BY satellite_id;
    """)

    print("Loading dim_sensor...")
    cur.execute("""
        INSERT INTO warehouse.dim_sensor (sensor_id, name, sensor_type, resolution)
        SELECT sensor_id, name, sensor_type, resolution
        FROM operational.sensor
        ORDER BY sensor_id;
    """)

    print("Loading dim_region...")
    cur.execute("""
        INSERT INTO warehouse.dim_region (region_id, name, region_type)
        SELECT region_id, name, region_type
        FROM operational.region
        ORDER BY region_id;
    """)

    print("Loading dim_land_cover...")
    cur.execute("""
        INSERT INTO warehouse.dim_land_cover (land_cover_id, name)
        SELECT land_cover_id, name
        FROM operational.land_cover
        ORDER BY land_cover_id;
    """)


def load_fact_observation(cur):
    """Extracts operational observation land cover measurements, joins with dimensions,
    and loads into warehouse.fact_observation enforcing the grain."""
    print("Loading fact_observation...")
    cur.execute("""
        INSERT INTO warehouse.fact_observation (
            satellite_key,
            sensor_key,
            region_key,
            date_key,
            land_cover_key,
            area,
            observation_count
        )
        SELECT
            ds.satellite_key,
            dse.sensor_key,
            dr.region_key,
            dd.date_key,
            dlc.land_cover_key,
            SUM(olc.area) AS area,
            COUNT(*) AS observation_count
        FROM operational.observation_land_cover olc
        JOIN operational.observation o
            ON olc.observation_id = o.observation_id
        JOIN operational.sensor s
            ON o.sensor_id = s.sensor_id
        JOIN warehouse.dim_sensor dse
            ON dse.sensor_id = s.sensor_id
        JOIN warehouse.dim_satellite ds
            ON ds.satellite_id = s.satellite_id
        JOIN warehouse.dim_region dr
            ON dr.region_id = o.region_id
        JOIN warehouse.dim_land_cover dlc
            ON dlc.land_cover_id = olc.land_cover_id
        JOIN warehouse.dim_date dd
            ON dd.date_key = TO_CHAR(o.observation_date, 'YYYYMMDD')::INTEGER
        GROUP BY
            ds.satellite_key,
            dse.sensor_key,
            dr.region_key,
            dd.date_key,
            dlc.land_cover_key;
    """)


def print_summary(cur):
    """Reports warehouse row counts."""
    tables = [
        "warehouse.dim_date",
        "warehouse.dim_satellite",
        "warehouse.dim_sensor",
        "warehouse.dim_region",
        "warehouse.dim_land_cover",
        "warehouse.fact_observation",
    ]
    print("\nWarehouse Row Counts:")
    for tbl in tables:
        cur.execute(f"SELECT COUNT(*) FROM {tbl};")
        count = cur.fetchone()[0]
        print(f"  {tbl:<28}: {count}")


def main():
    print("=" * 60)
    print("ETL Stage 2: Operational -> Data Warehouse (Star Schema)")
    print("=" * 60)

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("\nTruncating warehouse tables (idempotent reload)...")
        truncate_warehouse_tables(cur)

        print("\nExtracting & Loading Dimensions...")
        load_dimensions(cur)

        print("\nExtracting, Transforming & Loading Fact Observations...")
        load_fact_observation(cur)

        conn.commit()
        print("\n[SUCCESS] Warehouse ETL completed and committed successfully.")

        print_summary(cur)

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Warehouse ETL failed, rolled back: {e}", file=sys.stderr)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
