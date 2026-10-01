"""
stage1_operational_load.py

ETL Stage 1: EXTRACT the synthetic CSVs from etl/data/, VALIDATE and
CLEAN them, then LOAD them into the `operational` PostgreSQL/PostGIS
schema, in FK-dependency order.

Run:
    python etl/scripts/stage1_operational_load.py

Requires:
    pip install -r etl/requirements.txt --break-system-packages
    A running Postgres+PostGIS instance (see docker-compose.yml) with
    the schema from database/schema/*.sql already applied, and a
    ".env" file in the project root (copy .env.example -> .env).

This script is idempotent: it TRUNCATEs the operational tables
before reloading, so it is safe to re-run after fixing data or
schema issues.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extensions import register_adapter, AsIs
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# ---------------------------------------------------------------
# psycopg2 does not know how to adapt numpy's int64/float64 types
# (which pandas produces), so without this you get:
#   "can't adapt type 'numpy.int64'"
# Registering adapters here fixes it once, globally, for this script.
# ---------------------------------------------------------------
register_adapter(np.int64, lambda v: AsIs(v))
register_adapter(np.float64, lambda v: AsIs(v))

# ---------------------------------------------------------------
# 0. CONFIG
# ---------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "etl" / "data"

load_dotenv(PROJECT_ROOT / ".env")

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "satellite_db"),
    "user": os.getenv("POSTGRES_USER", "satellite_admin"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

REQUIRED_COLUMNS = {
    "satellites.csv": ["satellite_id", "name", "operator", "launch_date", "status"],
    "sensors.csv": ["sensor_id", "satellite_id", "name", "sensor_type", "resolution"],
    "regions.csv": ["region_id", "name", "region_type", "boundary_wkt"],
    "land_cover.csv": ["land_cover_id", "name", "description"],
    "observations.csv": ["observation_id", "sensor_id", "region_id",
                          "observation_date", "image_reference", "footprint_wkt"],
    "image_data.csv": ["image_id", "observation_id", "file_reference",
                        "format", "file_size", "acquisition_time"],
    "observation_land_cover.csv": ["observation_id", "land_cover_id", "area"],
    "change_event.csv": ["change_id", "region_id", "from_land_cover_id",
                          "to_land_cover_id", "start_date", "end_date", "changed_area"],
}

# Primary-key column(s) used for de-duplication during cleaning.
# Most tables have a single-column surrogate key (first column above),
# but observation_land_cover has a COMPOSITE key -- deduping on
# observation_id alone would wrongly discard valid rows for every
# land-cover type after the first one for a given observation.
PRIMARY_KEY_COLUMNS = {
    "satellites.csv": ["satellite_id"],
    "sensors.csv": ["sensor_id"],
    "regions.csv": ["region_id"],
    "land_cover.csv": ["land_cover_id"],
    "observations.csv": ["observation_id"],
    "image_data.csv": ["image_id"],
    "observation_land_cover.csv": ["observation_id", "land_cover_id"],
    "change_event.csv": ["change_id"],
}


# ---------------------------------------------------------------
# 1. EXTRACT + VALIDATE + CLEAN
# ---------------------------------------------------------------
def read_and_validate(filename):
    """Read a CSV, confirm required columns exist, drop rows with
    missing required values or duplicate primary keys, and report
    what was rejected. Returns a cleaned DataFrame."""
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Expected input file not found: {path}")

    df = pd.read_csv(path)

    missing_cols = [c for c in REQUIRED_COLUMNS[filename] if c not in df.columns]
    if missing_cols:
        raise ValueError(f"{filename}: missing required columns {missing_cols}")

    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS[filename])
    dropped = before - len(df)
    if dropped:
        print(f"  [{filename}] dropped {dropped} row(s) with missing required fields")

    pk_cols = PRIMARY_KEY_COLUMNS[filename]
    before = len(df)
    df = df.drop_duplicates(subset=pk_cols)
    deduped = before - len(df)
    if deduped:
        print(f"  [{filename}] dropped {deduped} duplicate row(s) on {pk_cols}")

    print(f"  [{filename}] {len(df)} valid row(s) ready to load")
    return df


# ---------------------------------------------------------------
# 2. LOAD helpers
# ---------------------------------------------------------------
def bulk_insert(cur, table, columns, rows, geom_columns=None):
    """Bulk insert rows using execute_values. geom_columns is a set
    of column names whose values are WKT strings that must be
    wrapped in ST_GeomFromText(..., 4326) rather than inserted raw."""
    geom_columns = geom_columns or set()

    col_list = ", ".join(columns)
    value_template_parts = [
        "ST_GeomFromText(%s, 4326)" if col in geom_columns else "%s"
        for col in columns
    ]
    value_template = "(" + ", ".join(value_template_parts) + ")"

    sql = f"INSERT INTO operational.{table} ({col_list}) VALUES %s"
    execute_values(cur, sql, rows, template=value_template)


def truncate_all(cur):
    """Wipe all operational tables (children first via CASCADE) so
    this script is safely re-runnable."""
    cur.execute("""
        TRUNCATE TABLE
            operational.change_event,
            operational.observation_land_cover,
            operational.image_data,
            operational.observation,
            operational.land_cover,
            operational.region,
            operational.sensor,
            operational.satellite
        RESTART IDENTITY CASCADE;
    """)


# ---------------------------------------------------------------
# 3. MAIN
# ---------------------------------------------------------------
def main():
    print("Reading + validating CSVs...")
    satellites = read_and_validate("satellites.csv")
    sensors = read_and_validate("sensors.csv")
    regions = read_and_validate("regions.csv")
    land_cover = read_and_validate("land_cover.csv")
    observations = read_and_validate("observations.csv")
    image_data = read_and_validate("image_data.csv")
    obs_land_cover = read_and_validate("observation_land_cover.csv")
    change_event = read_and_validate("change_event.csv")

    print("\nConnecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Truncating operational tables (idempotent reload)...")
        truncate_all(cur)

        print("Loading satellite...")
        bulk_insert(cur, "satellite",
                    ["satellite_id", "name", "operator", "launch_date", "status"],
                    list(satellites.itertuples(index=False, name=None)))

        print("Loading sensor...")
        bulk_insert(cur, "sensor",
                    ["sensor_id", "satellite_id", "name", "sensor_type", "resolution"],
                    list(sensors.itertuples(index=False, name=None)))

        print("Loading region (with PostGIS geometry)...")
        region_rows = list(regions[["region_id", "name", "region_type", "boundary_wkt"]]
                            .itertuples(index=False, name=None))
        bulk_insert(cur, "region",
                    ["region_id", "name", "region_type", "boundary"],
                    region_rows, geom_columns={"boundary"})

        print("Loading land_cover...")
        bulk_insert(cur, "land_cover",
                    ["land_cover_id", "name", "description"],
                    list(land_cover.itertuples(index=False, name=None)))

        print("Loading observation (with PostGIS geometry)...")
        obs_rows = list(observations[["observation_id", "sensor_id", "region_id",
                                       "observation_date", "image_reference", "footprint_wkt"]]
                         .itertuples(index=False, name=None))
        bulk_insert(cur, "observation",
                    ["observation_id", "sensor_id", "region_id", "observation_date",
                     "image_reference", "footprint"],
                    obs_rows, geom_columns={"footprint"})

        print("Loading image_data...")
        bulk_insert(cur, "image_data",
                    ["image_id", "observation_id", "file_reference", "format",
                     "file_size", "acquisition_time"],
                    list(image_data.itertuples(index=False, name=None)))

        print("Loading observation_land_cover...")
        bulk_insert(cur, "observation_land_cover",
                    ["observation_id", "land_cover_id", "area"],
                    list(obs_land_cover.itertuples(index=False, name=None)))

        print("Loading change_event...")
        bulk_insert(cur, "change_event",
                    ["change_id", "region_id", "from_land_cover_id", "to_land_cover_id",
                     "start_date", "end_date", "changed_area"],
                    list(change_event.itertuples(index=False, name=None)))

        conn.commit()
        print("\nAll tables loaded and committed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR during load, rolled back all changes: {e}", file=sys.stderr)
        raise
    finally:
        cur.close()
        conn.close()

    print("\nRow counts loaded:")
    print(f"  satellite               : {len(satellites)}")
    print(f"  sensor                  : {len(sensors)}")
    print(f"  region                  : {len(regions)}")
    print(f"  land_cover              : {len(land_cover)}")
    print(f"  observation             : {len(observations)}")
    print(f"  image_data              : {len(image_data)}")
    print(f"  observation_land_cover  : {len(obs_land_cover)}")
    print(f"  change_event            : {len(change_event)}")


if __name__ == "__main__":
    main()
