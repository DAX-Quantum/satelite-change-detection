-- =============================================================================
-- SATELLITE DATA MANAGEMENT & GEOSPATIAL CHANGE DETECTION
-- Script: 02_postgis_spatial_analysis.sql
-- Description: Advanced PostGIS Spatial Queries, GiST Indexing & Geodetics
-- Schema: operational
-- =============================================================================

SET search_path TO operational, public;

-- -----------------------------------------------------------------------------
-- 1. Exact Spatial Intersection and Metric Overlap %
-- Evaluates geometric overlap between satellite swath footprints and region polygons
-- Uses ::geography cast to evaluate metric surface areas over WGS84 spheroid
-- -----------------------------------------------------------------------------
SELECT 
    r.name AS region_name,
    r.region_type,
    s.name AS satellite_name,
    se.name AS sensor_name,
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
LIMIT 12;


-- -----------------------------------------------------------------------------
-- 2. Spatial Containment Check (ST_Contains)
-- Demonstrates topological predicate checking if swath completely contains region
-- -----------------------------------------------------------------------------
SELECT 
    o.observation_id,
    r.name AS region_name,
    o.observation_date,
    o.image_reference,
    ST_GeometryType(o.footprint) AS geom_type,
    ST_NPoints(o.footprint) AS footprint_vertices,
    ST_Contains(o.footprint, r.boundary) AS is_fully_contained
FROM operational.observation o
JOIN operational.region r ON o.region_id = r.region_id
ORDER BY is_fully_contained DESC, o.observation_date DESC
LIMIT 10;


-- -----------------------------------------------------------------------------
-- 3. Geodetic Centroid Distances (ST_Centroid & ST_Distance)
-- Computes great-circle physical distance in kilometers between region centers
-- -----------------------------------------------------------------------------
SELECT 
    r1.name AS origin_region,
    r2.name AS destination_region,
    ROUND(
        (ST_Distance(
            ST_Centroid(r1.boundary)::geography, 
            ST_Centroid(r2.boundary)::geography
        ) / 1000.0)::numeric, 
        2
    ) AS distance_km
FROM operational.region r1
CROSS JOIN operational.region r2
WHERE r1.region_id < r2.region_id
ORDER BY distance_km ASC;


-- -----------------------------------------------------------------------------
-- 4. Bounding Box GiST Index Evaluation (&& Operator vs ST_Intersects)
-- Stage 1: && tests fast bounding box overlap using GiST index
-- Stage 2: ST_Intersects performs exact topological polygon intersection
-- -----------------------------------------------------------------------------
EXPLAIN ANALYZE
SELECT 
    o.observation_id,
    r.name AS region_name,
    o.observation_date
FROM operational.observation o
JOIN operational.region r ON o.region_id = r.region_id
WHERE o.footprint && r.boundary
  AND ST_Intersects(o.footprint, r.boundary);


-- -----------------------------------------------------------------------------
-- 5. Export GeoJSON Feature Payload
-- Generates ready-to-consume GeoJSON strings for web GIS mapping engines
-- -----------------------------------------------------------------------------
SELECT 
    json_build_object(
        'type', 'Feature',
        'geometry', ST_AsGeoJSON(r.boundary)::json,
        'properties', json_build_object(
            'region_id', r.region_id,
            'name', r.name,
            'region_type', r.region_type,
            'area_sq_km', ROUND((ST_Area(r.boundary::geography) / 1000000.0)::numeric, 2)
        )
    ) AS geojson_feature
FROM operational.region r
LIMIT 5;
