"""
generate_sample_data.py

Generates SYNTHETIC sample data for the Satellite Data Management &
Geospatial Change Detection System.

IMPORTANT: All data produced by this script is synthetic. Satellite
and sensor names are fabricated for demonstration purposes. Urban
region boundaries use approximate real-world city locations (Delhi,
Mumbai, Bengaluru) purely as recognizable geographic anchors;
agricultural/forest/wetland regions are generic composites, not
references to any specific real protected area or farmland. No
row in this dataset represents an actual satellite observation.

Run:
    python etl/scripts/generate_sample_data.py

Output (into etl/data/):
    satellites.csv, sensors.csv, regions.csv, land_cover.csv,
    observations.csv, image_data.csv, observation_land_cover.csv,
    change_event.csv
"""

import csv
import random
from datetime import date, datetime
from pathlib import Path

random.seed(42)  # reproducible output

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------
# 1. SATELLITES
# ---------------------------------------------------------------
satellites = [
    {"satellite_id": 1, "name": "SYN-EO-1", "operator": "Synthetic Earth Observation Program",
     "launch_date": "2015-03-12", "status": "active"},
    {"satellite_id": 2, "name": "SYN-EO-2", "operator": "Synthetic Earth Observation Program",
     "launch_date": "2018-07-01", "status": "active"},
    {"satellite_id": 3, "name": "SYN-SAR-1", "operator": "Synthetic Earth Observation Program",
     "launch_date": "2020-11-23", "status": "active"},
]

# ---------------------------------------------------------------
# 2. SENSORS
# ---------------------------------------------------------------
sensors = [
    {"sensor_id": 1, "satellite_id": 1, "name": "MultiSpectral-A", "sensor_type": "Optical", "resolution": 10.0},
    {"sensor_id": 2, "satellite_id": 1, "name": "MultiSpectral-B", "sensor_type": "Optical", "resolution": 20.0},
    {"sensor_id": 3, "satellite_id": 2, "name": "HighRes-Pan", "sensor_type": "Optical", "resolution": 5.0},
    {"sensor_id": 4, "satellite_id": 2, "name": "MultiSpectral-C", "sensor_type": "Optical", "resolution": 15.0},
    {"sensor_id": 5, "satellite_id": 3, "name": "SAR-C-Band", "sensor_type": "Radar", "resolution": 25.0},
    {"sensor_id": 6, "satellite_id": 3, "name": "SAR-X-Band", "sensor_type": "Radar", "resolution": 12.0},
]

# ---------------------------------------------------------------
# 3. REGIONS (bbox polygons as WKT; SRID 4326 applied at load time)
# ---------------------------------------------------------------
def bbox_wkt(min_lon, min_lat, max_lon, max_lat):
    return (f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, "
            f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))")

regions = [
    {"region_id": 1, "name": "Delhi NCR", "region_type": "urban",
     "boundary_wkt": bbox_wkt(76.85, 28.40, 77.35, 28.90), "area_m2": 5.0e8},
    {"region_id": 2, "name": "Mumbai Metropolitan", "region_type": "urban",
     "boundary_wkt": bbox_wkt(72.75, 18.90, 72.98, 19.30), "area_m2": 4.0e8},
    {"region_id": 3, "name": "Bengaluru Urban", "region_type": "urban",
     "boundary_wkt": bbox_wkt(77.45, 12.85, 77.75, 13.10), "area_m2": 4.5e8},
    {"region_id": 4, "name": "Punjab Agricultural Belt (Synthetic)", "region_type": "agriculture",
     "boundary_wkt": bbox_wkt(75.00, 30.20, 75.60, 30.80), "area_m2": 8.0e8},
    {"region_id": 5, "name": "Central India Forest Belt (Synthetic)", "region_type": "forest",
     "boundary_wkt": bbox_wkt(80.00, 21.00, 80.60, 21.60), "area_m2": 7.0e8},
    {"region_id": 6, "name": "Eastern Coastal Wetland (Synthetic)", "region_type": "water",
     "boundary_wkt": bbox_wkt(86.30, 20.40, 86.80, 20.90), "area_m2": 3.0e8},
]

# ---------------------------------------------------------------
# 4. LAND COVER CATEGORIES
# ---------------------------------------------------------------
land_covers = [
    {"land_cover_id": 1, "name": "Forest", "description": "Dense tree canopy cover"},
    {"land_cover_id": 2, "name": "Urban", "description": "Built-up / impervious surface"},
    {"land_cover_id": 3, "name": "Water", "description": "Rivers, lakes, wetlands, reservoirs"},
    {"land_cover_id": 4, "name": "Agriculture", "description": "Cropland and cultivated land"},
    {"land_cover_id": 5, "name": "Barren", "description": "Bare soil / rock / unvegetated land"},
]
LC_BY_NAME = {lc["name"]: lc["land_cover_id"] for lc in land_covers}

# ---------------------------------------------------------------
# 5. TIME SERIES: quarterly observations, 2021-01-01 .. 2024-10-01
# ---------------------------------------------------------------
quarters = []
for year in range(2021, 2025):
    for month in (1, 4, 7, 10):
        quarters.append(date(year, month, 1))

# Starting % distribution and per-quarter drift, by region_type.
# These numbers are hand-tuned to produce *visible, explainable*
# trends (urban growth, deforestation, wetland shrinkage) -- not
# measured from any real dataset.
PROFILES = {
    "urban":       {"start": {"Forest": 10, "Urban": 55, "Water": 8, "Agriculture": 20, "Barren": 7},
                     "drift": {"Forest": -0.10, "Urban": 0.50, "Water": -0.05, "Agriculture": -0.30, "Barren": -0.05}},
    "agriculture": {"start": {"Forest": 8, "Urban": 5, "Water": 7, "Agriculture": 70, "Barren": 10},
                     "drift": {"Forest": 0.0, "Urban": 0.30, "Water": 0.0, "Agriculture": -0.25, "Barren": -0.05}},
    "forest":      {"start": {"Forest": 75, "Urban": 3, "Water": 5, "Agriculture": 10, "Barren": 7},
                     "drift": {"Forest": -0.40, "Urban": 0.10, "Water": 0.0, "Agriculture": 0.25, "Barren": 0.05}},
    "water":       {"start": {"Forest": 10, "Urban": 4, "Water": 65, "Agriculture": 15, "Barren": 6},
                     "drift": {"Forest": 0.0, "Urban": 0.10, "Water": -0.30, "Agriculture": 0.15, "Barren": 0.05}},
}

def pct_at_t(region_type, t):
    profile = PROFILES[region_type]
    raw = {}
    for lc_name, start_val in profile["start"].items():
        drift = profile["drift"][lc_name]
        jitter = random.uniform(-0.3, 0.3)
        raw[lc_name] = max(0.5, start_val + drift * t + jitter)
    total = sum(raw.values())
    return {k: (v / total) * 100 for k, v in raw.items()}

observations = []
image_data = []
observation_land_cover = []

obs_id = 1
img_id = 1
year_snapshot = {}  # (region_id, year) -> {lc_name: area}  -- for change_event

for region in regions:
    for t, qdate in enumerate(quarters):
        sensor = sensors[(region["region_id"] + t) % len(sensors)]
        footprint_wkt = region["boundary_wkt"]  # full-region observation

        observations.append({
            "observation_id": obs_id,
            "sensor_id": sensor["sensor_id"],
            "region_id": region["region_id"],
            "observation_date": qdate.isoformat(),
            "image_reference": f"SYN_IMG_{obs_id:04d}.tif",
            "footprint_wkt": footprint_wkt,
        })

        image_data.append({
            "image_id": img_id,
            "observation_id": obs_id,
            "file_reference": f"/synthetic/images/SYN_IMG_{obs_id:04d}.tif",
            "format": "GeoTIFF",
            "file_size": random.randint(50_000_000, 500_000_000),
            "acquisition_time": datetime.combine(qdate, datetime.min.time())
                                 .replace(hour=random.randint(5, 10),
                                          minute=random.randint(0, 59)).isoformat(sep=" "),
        })

        pct = pct_at_t(region["region_type"], t)
        areas = {name: round((p / 100.0) * region["area_m2"], 2) for name, p in pct.items()}

        for lc_name, area in areas.items():
            observation_land_cover.append({
                "observation_id": obs_id,
                "land_cover_id": LC_BY_NAME[lc_name],
                "area": area,
            })

        if qdate.month == 1:
            year_snapshot[(region["region_id"], qdate.year)] = areas

        img_id += 1
        obs_id += 1

# ---------------------------------------------------------------
# 6. CHANGE_EVENT: year-over-year dominant shift per region
# ---------------------------------------------------------------
change_events = []
change_id = 1
years = [2021, 2022, 2023, 2024]

for region in regions:
    for y1, y2 in zip(years, years[1:]):
        a1 = year_snapshot.get((region["region_id"], y1))
        a2 = year_snapshot.get((region["region_id"], y2))
        if not a1 or not a2:
            continue
        deltas = {name: a2[name] - a1[name] for name in a1}
        to_name = max(deltas, key=deltas.get)     # biggest gain
        from_name = min(deltas, key=deltas.get)    # biggest loss
        if to_name == from_name:
            continue
        changed_area = round(deltas[to_name], 2)
        if changed_area <= 0:
            continue
        change_events.append({
            "change_id": change_id,
            "region_id": region["region_id"],
            "from_land_cover_id": LC_BY_NAME[from_name],
            "to_land_cover_id": LC_BY_NAME[to_name],
            "start_date": date(y1, 1, 1).isoformat(),
            "end_date": date(y2, 1, 1).isoformat(),
            "changed_area": changed_area,
        })
        change_id += 1

# ---------------------------------------------------------------
# 7. WRITE CSVs
# ---------------------------------------------------------------
def write_csv(filename, rows, fieldnames):
    path = OUT_DIR / filename
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows):4d} rows -> {path}")

write_csv("satellites.csv", satellites, ["satellite_id", "name", "operator", "launch_date", "status"])
write_csv("sensors.csv", sensors, ["sensor_id", "satellite_id", "name", "sensor_type", "resolution"])
write_csv("regions.csv",
          [{"region_id": r["region_id"], "name": r["name"], "region_type": r["region_type"],
            "boundary_wkt": r["boundary_wkt"]} for r in regions],
          ["region_id", "name", "region_type", "boundary_wkt"])
write_csv("land_cover.csv", land_covers, ["land_cover_id", "name", "description"])
write_csv("observations.csv", observations,
          ["observation_id", "sensor_id", "region_id", "observation_date", "image_reference", "footprint_wkt"])
write_csv("image_data.csv", image_data,
          ["image_id", "observation_id", "file_reference", "format", "file_size", "acquisition_time"])
write_csv("observation_land_cover.csv", observation_land_cover,
          ["observation_id", "land_cover_id", "area"])
write_csv("change_event.csv", change_events,
          ["change_id", "region_id", "from_land_cover_id", "to_land_cover_id",
           "start_date", "end_date", "changed_area"])

print("\nAll synthetic data generated successfully.")
print("Reminder: this data is entirely SYNTHETIC and for demonstration only.")
