# Entity-Relationship (ER) & Relational Schema Diagrams
## Satellite Data Management and Geospatial Change Detection System
**Track C — Data Warehouse and Analytics**

---

## 1. Overview of the Dual-Schema Architecture

The system features two complementary database schemas:
1. **Operational Schema (`operational`)**: Modeled in **Third Normal Form (3NF)** with PostGIS spatial types for transactional reliability and spatial topology.
2. **Data Warehouse Schema (`warehouse`)**: Modeled as a **Star Schema** with surrogate keys and an explicit grain for Online Analytical Processing (OLAP).

---

## 2. Operational Schema (3NF) — Entity-Relationship Diagram

### 2.1 Mermaid Diagram

```mermaid
erDiagram
    SATELLITE ||--o{ SENSOR : "carries (1:N)"
    SENSOR ||--o{ OBSERVATION : "produces (1:N)"
    REGION ||--o{ OBSERVATION : "is observed by (1:N)"
    OBSERVATION ||--o{ IMAGE_DATA : "has (1:N)"
    OBSERVATION ||--o{ OBSERVATION_LAND_COVER : "measures (1:N)"
    LAND_COVER ||--o{ OBSERVATION_LAND_COVER : "appears in (1:N)"
    REGION ||--o{ CHANGE_EVENT : "undergoes (1:N)"
    LAND_COVER ||--o{ CHANGE_EVENT : "from_land_cover_id (1:N)"
    LAND_COVER ||--o{ CHANGE_EVENT : "to_land_cover_id (1:N)"

    SATELLITE {
        int satellite_id PK
        varchar name
        varchar operator
        date launch_date
        varchar status
    }

    SENSOR {
        int sensor_id PK
        int satellite_id FK
        varchar name
        varchar sensor_type
        numeric resolution
    }

    REGION {
        int region_id PK
        varchar name
        varchar region_type
        geometry boundary "POLYGON 4326"
    }

    OBSERVATION {
        int observation_id PK
        int sensor_id FK
        int region_id FK
        date observation_date
        varchar image_reference
        geometry footprint "POLYGON 4326"
    }

    IMAGE_DATA {
        int image_id PK
        int observation_id FK
        varchar file_reference
        varchar format
        bigint file_size
        timestamp acquisition_time
    }

    LAND_COVER {
        int land_cover_id PK
        varchar name UK
        text description
    }

    OBSERVATION_LAND_COVER {
        int observation_id PK, FK
        int land_cover_id PK, FK
        numeric area "m2"
    }

    CHANGE_EVENT {
        int change_id PK
        int region_id FK
        int from_land_cover_id FK
        int to_land_cover_id FK
        date start_date
        date end_date
        numeric changed_area "m2"
    }
```

### 2.2 Visual Architecture Diagram Render
An SVG and high-resolution render of the relational schema is available in the repository:
- **Vector Graphic:** [er_diagram.svg](file:///d:/dbms%20project/satelite-change-detection/docs/er_diagram.svg)
- **High-Res Graphic:** [er_diagram.jpg](file:///d:/dbms%20project/satelite-change-detection/docs/er_diagram.jpg)
- **Interactive Browser Viewer:** [view_er_diagram.html](file:///d:/dbms%20project/satelite-change-detection/docs/view_er_diagram.html)

---

## 3. Data Warehouse Schema — Star Schema Diagram

### 3.1 Mermaid Star Schema

```mermaid
erDiagram
    DIM_SATELLITE   ||--o{ FACT_OBSERVATION : "satellite_key (1:N)"
    DIM_SENSOR      ||--o{ FACT_OBSERVATION : "sensor_key (1:N)"
    DIM_REGION      ||--o{ FACT_OBSERVATION : "region_key (1:N)"
    DIM_DATE        ||--o{ FACT_OBSERVATION : "date_key (1:N)"
    DIM_LAND_COVER  ||--o{ FACT_OBSERVATION : "land_cover_key (1:N)"

    FACT_OBSERVATION {
        int observation_fact_key PK
        int satellite_key FK
        int sensor_key FK
        int region_key FK
        int date_key FK
        int land_cover_key FK
        numeric area "measure, m2"
        int observation_count "measure"
    }

    DIM_SATELLITE {
        int satellite_key PK
        int satellite_id "natural key"
        varchar name
        varchar operator
        varchar status
    }

    DIM_SENSOR {
        int sensor_key PK
        int sensor_id "natural key"
        varchar name
        varchar sensor_type
        numeric resolution
    }

    DIM_REGION {
        int region_key PK
        int region_id "natural key"
        varchar name
        varchar region_type
    }

    DIM_DATE {
        int date_key PK "YYYYMMDD"
        date full_date UK
        int day
        int month
        varchar month_name
        int quarter
        int year
    }

    DIM_LAND_COVER {
        int land_cover_key PK
        int land_cover_id "natural key"
        varchar name
    }
```

---

## 4. Relationship & Cardinality Reference Table

| Parent Entity | Child Entity | Relationship Type | Foreign Key Attribute | Enforcement Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| `SATELLITE` | `SENSOR` | 1 to Many (1:N) | `sensor.satellite_id` | `NOT NULL REFERENCES satellite(satellite_id)` |
| `SENSOR` | `OBSERVATION` | 1 to Many (1:N) | `observation.sensor_id` | `NOT NULL REFERENCES sensor(sensor_id)` |
| `REGION` | `OBSERVATION` | 1 to Many (1:N) | `observation.region_id` | `NOT NULL REFERENCES region(region_id)` |
| `OBSERVATION` | `IMAGE_DATA` | 1 to Many (1:N) | `image_data.observation_id` | `NOT NULL REFERENCES observation(observation_id)` |
| `OBSERVATION` | `OBS_LAND_COVER`| 1 to Many (1:N) | `obs_land_cover.observation_id` | Composite PK + FK |
| `LAND_COVER` | `OBS_LAND_COVER`| 1 to Many (1:N) | `obs_land_cover.land_cover_id` | Composite PK + FK |
| `REGION` | `CHANGE_EVENT` | 1 to Many (1:N) | `change_event.region_id` | `NOT NULL REFERENCES region(region_id)` |
| `LAND_COVER` | `CHANGE_EVENT` | 1 to Many (1:N) | `change_event.from_land_cover_id` | `NOT NULL REFERENCES land_cover(land_cover_id)` |
| `LAND_COVER` | `CHANGE_EVENT` | 1 to Many (1:N) | `change_event.to_land_cover_id` | `NOT NULL REFERENCES land_cover(land_cover_id)` |
