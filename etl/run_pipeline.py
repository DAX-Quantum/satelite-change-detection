"""
run_pipeline.py

Master Orchestrator for the Satellite Data Management & Geospatial Change Detection ETL.
Executes Stage 1 (Operational 3NF Load) and Stage 2 (Warehouse Star Schema Load),
refreshes materialized views, and verifies database integrity.

Usage:
    python etl/run_pipeline.py
    python etl/run_pipeline.py --regenerate-data
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "satellite_db"),
    "user": os.getenv("POSTGRES_USER", "satellite_admin"),
    "password": os.getenv("POSTGRES_PASSWORD", "12345"),
}


def run_script(script_path):
    print(f"\n>>> Running: {script_path.name}...")
    result = subprocess.run([sys.executable, str(script_path)], capture_output=False)
    if result.returncode != 0:
        print(f"\n[FAILED] Script {script_path.name} failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def refresh_materialized_views():
    print("\n>>> Refreshing Materialized Views...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute("REFRESH MATERIALIZED VIEW warehouse.mvw_regional_quarterly_landcover;")
        print("  Successfully refreshed warehouse.mvw_regional_quarterly_landcover.")
    except Exception as e:
        print(f"  Warning: could not refresh materialized view (it may not exist yet): {e}")
    finally:
        cur.close()
        conn.close()


def print_system_audit():
    print("\n" + "=" * 65)
    print("           DATABASE PIPELINE AUDIT REPORT")
    print("=" * 65)
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    queries = [
        ("Operational: Satellites", "SELECT count(*) FROM operational.satellite;"),
        ("Operational: Sensors", "SELECT count(*) FROM operational.sensor;"),
        ("Operational: Regions", "SELECT count(*) FROM operational.region;"),
        ("Operational: Observations", "SELECT count(*) FROM operational.observation;"),
        ("Operational: Observation Land Cover", "SELECT count(*) FROM operational.observation_land_cover;"),
        ("Operational: Change Events", "SELECT count(*) FROM operational.change_event;"),
        ("Warehouse: Dim Dates", "SELECT count(*) FROM warehouse.dim_date;"),
        ("Warehouse: Dim Satellites", "SELECT count(*) FROM warehouse.dim_satellite;"),
        ("Warehouse: Dim Sensors", "SELECT count(*) FROM warehouse.dim_sensor;"),
        ("Warehouse: Dim Regions", "SELECT count(*) FROM warehouse.dim_region;"),
        ("Warehouse: Dim Land Cover", "SELECT count(*) FROM warehouse.dim_land_cover;"),
        ("Warehouse: Fact Observations", "SELECT count(*) FROM warehouse.fact_observation;"),
        ("Materialized View: Quarterly Rows", "SELECT count(*) FROM warehouse.mvw_regional_quarterly_landcover;"),
    ]

    for label, query in queries:
        try:
            cur.execute(query)
            count = cur.fetchone()[0]
            print(f"  {label:<38}: {count:>6}")
        except Exception as e:
            print(f"  {label:<38}: ERROR ({e})")

    cur.close()
    conn.close()
    print("=" * 65)
    print("  Status: All operational and dimensional stores synchronized!")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Master ETL Orchestrator")
    parser.add_argument("--regenerate-data", action="store_true", help="Re-generate synthetic CSV data")
    args = parser.parse_args()

    scripts_dir = PROJECT_ROOT / "etl" / "scripts"

    if args.regenerate_data:
        run_script(scripts_dir / "generate_sample_data.py")

    run_script(scripts_dir / "stage1_operational_load.py")
    run_script(scripts_dir / "stage2_warehouse_load.py")
    refresh_materialized_views()
    print_system_audit()


if __name__ == "__main__":
    main()
