/**
 * map.js - Leaflet.js Geospatial Map Controller with Vibrant Theming
 * Visualizes PostGIS Polygons for Monitored Regions and Satellite Footprints
 */

let mapInstance = null;
let regionsLayer = null;
let footprintsLayer = null;

const REGION_COLORS = {
  urban: '#f43f5e',       // Vivid Neon Rose
  forest: '#10b981',      // Lush Emerald
  agriculture: '#fbbf24', // Radiant Golden Amber
  water: '#00f2fe',       // Electric Cyan
  wetland: '#00f2fe',     // Electric Cyan
  default: '#a855f7'      // Cosmic Purple
};

function initMap() {
  if (mapInstance) return;

  const mapContainer = document.getElementById('map-container');
  if (!mapContainer) return;

  // Initialize Leaflet map centered over India
  mapInstance = L.map('map-container', {
    zoomControl: true,
    attributionControl: false
  }).setView([22.5937, 78.9629], 5);

  // CartoDB DarkMatter tiles for sleek cyber/space aesthetics
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 18,
    subdomains: 'abcd',
  }).addTo(mapInstance);

  // Load GeoJSON layers from PostGIS API
  loadRegionsLayer();
  loadFootprintsLayer();
}

async function loadRegionsLayer() {
  try {
    const res = await fetch('/api/spatial/regions');
    if (!res.ok) throw new Error('Failed to load regions');
    const geojsonData = await res.json();

    if (regionsLayer && mapInstance) {
      mapInstance.removeLayer(regionsLayer);
    }

    regionsLayer = L.geoJSON(geojsonData, {
      style: (feature) => {
        const type = feature.properties.region_type?.toLowerCase() || 'default';
        const color = REGION_COLORS[type] || REGION_COLORS.default;
        return {
          color: color,
          weight: 3,
          opacity: 0.95,
          fillColor: color,
          fillOpacity: 0.30,
          dashArray: '5, 4'
        };
      },
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        const type = p.region_type?.toLowerCase() || 'default';
        const signatureColor = REGION_COLORS[type] || REGION_COLORS.default;
        
        layer.on({
          mouseover: (e) => {
            const target = e.target;
            target.setStyle({
              weight: 4.5,
              fillOpacity: 0.55,
              dashArray: ''
            });
            updateRegionDetailCard(p);
          },
          mouseout: (e) => {
            regionsLayer.resetStyle(e.target);
          },
          click: (e) => {
            mapInstance.fitBounds(e.target.getBounds(), { padding: [50, 50], maxZoom: 9 });
            updateRegionDetailCard(p);
            
            // Auto-filter change comparison tab
            const regionSelect = document.getElementById('compare-region-select');
            if (regionSelect) {
              regionSelect.value = p.region_id;
              window.triggerComparison?.();
            }
          }
        });

        layer.bindPopup(`
          <div style="font-family: 'Inter', sans-serif; background: #070c1d; color: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid ${signatureColor}; box-shadow: 0 4px 20px rgba(0,0,0,0.8);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <strong style="font-size: 14px; color: #ffffff; font-weight: 700;">${p.name}</strong>
              <span style="font-size: 10px; padding: 2px 6px; border-radius: 4px; background: ${signatureColor}22; color: ${signatureColor}; border: 1px solid ${signatureColor}; font-weight: 700; text-transform: uppercase;">
                ${p.region_type}
              </span>
            </div>
            <div style="font-size: 11px; color: #94a3b8; margin-bottom: 8px;">PostGIS Spatial Polygon (EPSG:4326)</div>
            <div style="font-size: 12px; line-height: 1.6; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px;">
              <div>• <b>Geodetic Area:</b> <span style="color: #00f2fe; font-weight: 600;">${p.area_sq_km.toLocaleString()} km²</span></div>
              <div>• <b>Observation Passes:</b> <span style="color: #00f5a0; font-weight: 600;">${p.observation_count}</span></div>
              <div>• <b>Historical Change Events:</b> <span style="color: #f43f5e; font-weight: 600;">${p.change_events_count}</span></div>
            </div>
          </div>
        `);
      }
    }).addTo(mapInstance);

  } catch (err) {
    console.error('Error rendering regions layer:', err);
  }
}

async function loadFootprintsLayer() {
  try {
    const res = await fetch('/api/spatial/observations?limit=40');
    if (!res.ok) throw new Error('Failed to load observation footprints');
    const geojsonData = await res.json();

    if (footprintsLayer && mapInstance) {
      mapInstance.removeLayer(footprintsLayer);
    }

    footprintsLayer = L.geoJSON(geojsonData, {
      style: () => ({
        color: '#00f2fe',
        weight: 1.5,
        opacity: 0.75,
        fillColor: '#0284c7',
        fillOpacity: 0.12,
        dashArray: '3, 3'
      }),
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        layer.bindPopup(`
          <div style="font-family: 'Inter', sans-serif; background: #070c1d; color: #f8fafc; padding: 8px; border-radius: 6px; border: 1px solid #00f2fe;">
            <strong style="font-size: 13px; color: #00f2fe;">${p.image_reference}</strong><br/>
            <span style="font-size: 11px; color: #c084fc; font-weight: 600;">${p.satellite_name} • ${p.sensor_name}</span>
            <hr style="margin: 6px 0; border: none; border-top: 1px solid rgba(255,255,255,0.1);"/>
            <div style="font-size: 11px; line-height: 1.5; color: #cbd5e1;">
              <div>Date: <b>${p.observation_date}</b></div>
              <div>Ground Resolution: <b>${p.resolution}m/px</b></div>
            </div>
          </div>
        `);
      }
    });

    // Default to enabled
    footprintsLayer.addTo(mapInstance);

  } catch (err) {
    console.error('Error rendering footprints layer:', err);
  }
}

function toggleFootprints(visible) {
  if (!mapInstance || !footprintsLayer) return;
  if (visible) {
    mapInstance.addLayer(footprintsLayer);
  } else {
    mapInstance.removeLayer(footprintsLayer);
  }
}

function updateRegionDetailCard(p) {
  const container = document.getElementById('selected-region-details');
  if (!container) return;

  const type = p.region_type?.toLowerCase() || 'default';
  const color = REGION_COLORS[type] || REGION_COLORS.default;

  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <h4 style="font-size: 16px; color: #ffffff; font-weight: 700; font-family: var(--font-heading);">${p.name}</h4>
      <span class="badge ${p.region_type}">${p.region_type}</span>
    </div>
    <div style="color: var(--neon-cyan); font-size: 11px; font-weight: 600; text-transform: uppercase; margin-bottom: 10px;">
      PostGIS GEOMETRY(POLYGON, 4326)
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; margin-bottom: 10px;">
      <div style="background: rgba(255,255,255,0.04); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
        <span style="color: var(--text-muted); display: block; font-size: 10px; text-transform: uppercase; font-weight: 700;">Surface Area</span>
        <strong style="font-size: 15px; color: #ffffff; font-family: var(--font-heading);">${p.area_sq_km.toLocaleString()} km²</strong>
      </div>
      <div style="background: rgba(255,255,255,0.04); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
        <span style="color: var(--text-muted); display: block; font-size: 10px; text-transform: uppercase; font-weight: 700;">Image Passes</span>
        <strong style="font-size: 15px; color: var(--neon-cyan); font-family: var(--font-heading);">${p.observation_count} Swaths</strong>
      </div>
    </div>
    <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.25); padding: 8px 12px; border-radius: 6px; font-size: 11px; color: var(--neon-rose); margin-bottom: 8px;">
      Detected Shift Events: <b>${p.change_events_count} Historical Anomalies</b>
    </div>
    <div style="font-size: 11px; color: var(--text-dim); font-family: var(--font-mono);">
      Centroid: ${p.centroid[0].toFixed(3)}°N, ${p.centroid[1].toFixed(3)}°E
    </div>
  `;
}

// Invalidate size on tab activation
function resizeMap() {
  if (mapInstance) {
    setTimeout(() => mapInstance.invalidateSize(), 200);
  }
}
