# Database Normalization & Functional Dependencies
## Satellite Data Management and Geospatial Change Detection System
**Course:** DBMS Laboratory Course Project  
**Selected Track:** Track C — Data Warehouse and Analytics  

---

## 1. Executive Summary
Normalization is the systematic process of decomposing relational tables to eliminate data redundancy and prevent insertion, update, and deletion anomalies. In this project:
- The **`operational` schema** is strictly normalized up to **Third Normal Form (3NF)**.
- The **`warehouse` schema** features **intentional, controlled denormalization** within dimension tables (e.g., `dim_date`) to optimize analytical query throughput.

---

## 2. Functional Dependencies (FDs) Analysis

A functional dependency $\alpha \rightarrow \beta$ holds on a relation $R$ if and only if for any two tuples $t_1, t_2 \in R$, whenever $t_1[\alpha] = t_2[\alpha]$, it must also hold that $t_1[\beta] = t_2[\beta]$.

### Table-by-Table Functional Dependencies:

#### 1. `SATELLITE`
- Candidate Key / Primary Key: `{satellite_id}`
- Functional Dependencies:
  $$\text{satellite\_id} \rightarrow \{\text{name}, \text{operator}, \text{launch\_date}, \text{status}\}$$
- Explanation: The primary key determines all attributes. No non-prime attribute determines another non-prime attribute.

#### 2. `SENSOR`
- Candidate Key / Primary Key: `{sensor_id}`
- Alternate Key: `{(satellite_id, name)}`
- Functional Dependencies:
  $$\text{sensor\_id} \rightarrow \{\text{satellite\_id}, \text{name}, \text{sensor\_type}, \text{resolution}\}$$
  $$\{\text{satellite\_id}, \text{name}\} \rightarrow \{\text{sensor\_id}, \text{sensor\_type}, \text{resolution}\}$$

#### 3. `REGION`
- Candidate Key / Primary Key: `{region_id}`
- Functional Dependencies:
  $$\text{region\_id} \rightarrow \{\text{name}, \text{region\_type}, \text{boundary}\}$$

#### 4. `OBSERVATION`
- Candidate Key / Primary Key: `{observation_id}`
- Functional Dependencies:
  $$\text{observation\_id} \rightarrow \{\text{sensor\_id}, \text{region\_id}, \text{observation\_date}, \text{image\_reference}, \text{footprint}\}$$

#### 5. `IMAGE_DATA`
- Candidate Key / Primary Key: `{image_id}`
- Functional Dependencies:
  $$\text{image\_id} \rightarrow \{\text{observation\_id}, \text{file\_reference}, \text{format}, \text{file\_size}, \text{acquisition\_time}\}$$

#### 6. `LAND_COVER`
- Candidate Key / Primary Key: `{land_cover_id}`
- Alternate Key: `{name}`
- Functional Dependencies:
  $$\text{land\_cover\_id} \rightarrow \{\text{name}, \text{description}\}$$
  $$\text{name} \rightarrow \{\text{land\_cover\_id}, \text{description}\}$$

#### 7. `OBSERVATION_LAND_COVER` (Associative Entity)
- Composite Primary Key: `{(observation_id, land_cover_id)}`
- Functional Dependency:
  $$\{\text{observation\_id}, \text{land\_cover\_id}\} \rightarrow \{\text{area}\}$$
- **Crucial Viva Insight:** The measurement `area` depends on the **entire composite key**, not on `observation_id` alone (one observation measures multiple land-cover classes) nor on `land_cover_id` alone (one land-cover class exists in multiple observations).

#### 8. `CHANGE_EVENT`
- Candidate Key / Primary Key: `{change_id}`
- Functional Dependencies:
  $$\text{change\_id} \rightarrow \{\text{region\_id}, \text{from\_land\_cover\_id}, \text{to\_land\_cover\_id}, \text{start\_date}, \text{end\_date}, \text{changed\_area}\}$$

---

## 3. Step-by-Step Normalization Proof

### 3.1 First Normal Form (1NF)
**Definition:** A relation is in 1NF if and only if all domain values are atomic (indivisible) and there are no repeating groups or multi-valued attributes.

- **Non-1NF Violation Prevented:**
  If we had stored land cover as a comma-separated string inside `OBSERVATION`:
  ```
  observation_id: 101, land_covers: "Forest, Urban, Water"  <-- VIOLATES 1NF
  ```
  Querying "total area of Forest" would require expensive string parsing and regex matches.
- **1NF Compliance:**
  Each land-cover measurement is stored in its own atomic row inside the associative table `OBSERVATION_LAND_COVER`. Every attribute holds a single scalar value.

---

### 3.2 Second Normal Form (2NF)
**Definition:** A relation is in 2NF if and only if it is in 1NF and **no non-prime attribute is partially dependent on any candidate key**. (Applies to tables with composite candidate keys).

- **Partial Dependency Scenario:**
  Consider a hypothetical unnormalized table:
  `MEASUREMENT(observation_id, land_cover_id, land_cover_name, area)`
  - Composite Key: `(observation_id, land_cover_id)`
  - Functional Dependency: `land_cover_id -> land_cover_name`
  - *Problem:* `land_cover_name` depends on only a subset (`land_cover_id`) of the composite key. This is a **partial dependency**, causing update anomalies if a land cover is renamed.
- **2NF Resolution:**
  Decompose into:
  1. `LAND_COVER(land_cover_id, name, description)` — where `land_cover_id -> name`.
  2. `OBSERVATION_LAND_COVER(observation_id, land_cover_id, area)` — where `(observation_id, land_cover_id) -> area`.
  `area` depends on the **full composite key**, achieving full functional dependency. Hence, the relation is in 2NF.

---

### 3.3 Third Normal Form (3NF)
**Definition:** A relation is in 3NF if and only if it is in 2NF and **no non-prime attribute is transitively dependent on the primary key**. (i.e., for every non-trivial FD $X \rightarrow Y$, either $X$ is a superkey, or $Y$ is a prime attribute).

- **Transitive Dependency Scenario:**
  Suppose `OBSERVATION` stored satellite information:
  `OBSERVATION(observation_id, observation_date, sensor_id, sensor_name, satellite_id, satellite_name)`
  - FDs:
    $$\text{observation\_id} \rightarrow \text{sensor\_id}$$
    $$\text{sensor\_id} \rightarrow \text{satellite\_id}$$
    $$\text{satellite\_id} \rightarrow \text{satellite\_name}$$
  - *Problem:* `satellite_name` transitively depends on `observation_id` via `sensor_id` and `satellite_id`.
  - *Anomalies Caused:*
    - *Insertion Anomaly:* Cannot record a new satellite without first recording an observation.
    - *Deletion Anomaly:* Deleting the last observation for a sensor deletes the satellite's metadata.
    - *Update Anomaly:* If a satellite operator updates its name, hundreds of observation rows must be updated.
- **3NF Resolution:**
  Decompose into three distinct tables:
  1. `SATELLITE(satellite_id, name, operator, launch_date, status)`
  2. `SENSOR(sensor_id, satellite_id, name, sensor_type, resolution)`
  3. `OBSERVATION(observation_id, sensor_id, region_id, observation_date, footprint, ...)`
  Now every non-prime attribute depends directly on the key, the whole key, and nothing but the key!

---

## 4. Justification of Intentional Warehouse Denormalization

While the operational database is in 3NF, the **Data Warehouse (`warehouse` schema)** deliberately introduces controlled denormalization:

1. **`dim_date` Table:**
   - Pre-computed attributes: `year`, `quarter`, `month`, `month_name`, `day`.
   - *Normalization purist critique:* `month -> quarter` and `date -> month` represent transitive dependencies.
   - *OLAP Justification:* Normalizing dates into separate `Day`, `Month`, `Quarter`, `Year` tables (a Snowflake Schema) would require 4 additional table joins for every single analytical aggregation. Pre-populating a flattened dimension table eliminates joins and drastically improves query performance.
2. **Surrogate Keys vs. Natural Keys:**
   - Dimension tables assign independent surrogate keys (`satellite_key SERIAL`). This isolates analytical history from operational key updates, re-indexing, or administrative purges.
