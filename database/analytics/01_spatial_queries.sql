-- =========================================================
-- 01_spatial_queries.sql
-- PostGIS Spatial Analysis Queries (Operational Schema)
-- Designed for DBMS Project Demonstration & Viva Voce
-- =========================================================

SET search_path TO operational, public;

-- ---------------------------------------------------------
-- QUERY 1: Observation Coverage Analysis
-- Check the percentage of region area covered by each satellite footprint
-- using ST_Intersection and ST_Area (transformed to metric coordinate system)
-- ---------------------------------------------------------
SELECT 
    r.name AS region_name,
    r.region_type,
    s.name AS satellite_name,
    o.observation_date,
    ROUND((ST_Area(ST_Intersection(r.boundary, o.footprint)::geography) / 1000000.0)::numeric, 2) AS covered_area_sq_km,
    ROUND((ST_Area(r.boundary::geography) / 1000000.0)::numeric, 2) AS total_region_area_sq_km,
    ROUND(
        (ST_Area(ST_Intersection(r.boundary, o.footprint)::geography) / 
         NULLIF(ST_Area(r.boundary::geography), 0) * 100.0)::numeric, 
        2
    ) AS coverage_percentage
FROM operational.observation o
JOIN operational.region r ON o.region_id = r.region_id
JOIN operational.sensor se ON o.sensor_id = se.sensor_id
JOIN operational.satellite s ON se.satellite_id = s.satellite_id
WHERE ST_Intersects(r.boundary, o.footprint)
ORDER BY coverage_percentage DESC
LIMIT 10;


-- ---------------------------------------------------------
-- QUERY 2: Spatial Containment Check
-- Find observations where the satellite footprint completely contains the region
-- Demonstrates ST_Contains and spatial GiST index usage
-- ---------------------------------------------------------
SELECT 
    o.observation_id,
    r.name AS region_name,
    o.observation_date,
    o.image_reference,
    ST_GeometryType(o.footprint) AS geom_type,
    ST_NPoints(o.footprint) AS footprint_vertices
FROM operational.observation o
JOIN operational.region r ON o.region_id = r.region_id
WHERE ST_Contains(o.footprint, r.boundary);


-- ---------------------------------------------------------
-- QUERY 3: Distance Between Regions
-- Computes geodetic distance between centroids of monitored regions in Kilometers
-- Demonstrates ST_Centroid and ST_Distance on geography types
-- ---------------------------------------------------------
SELECT 
    r1.name AS region_1,
    r2.name AS region_2,
    ROUND((ST_Distance(ST_Centroid(r1.boundary)::geography, ST_Centroid(r2.boundary)::geography) / 1000.0)::numeric, 2) AS distance_km
FROM operational.region r1
CROSS JOIN operational.region r2
WHERE r1.region_id < r2.region_id
ORDER BY distance_km ASC;


-- ---------------------------------------------------------
-- QUERY 4: Export PostGIS Geometry as GeoJSON
-- Essential for Web Mapping (Leaflet / Mapbox integration)
-- ---------------------------------------------------------
SELECT 
    region_id,
    name,
    region_type,
    ST_AsGeoJSON(boundary) AS geojson_geometry
FROM operational.region;
