/**
 * map.js - Leaflet.js Geospatial Map Controller
 * Visualizes PostGIS Polygons for Monitored Regions and Satellite Footprints
 */

let mapInstance = null;
let regionsLayer = null;
let footprintsLayer = null;

const REGION_COLORS = {
  urban: '#f43f5e',       // Rose
  forest: '#10b981',      // Emerald
  agriculture: '#f59e0b', // Amber
  water: '#06b6d4',       // Cyan
  default: '#8b5cf6'      // Purple
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

  // CartoDB DarkMatter tiles for dark aesthetics
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
          weight: 2.5,
          opacity: 0.9,
          fillColor: color,
          fillOpacity: 0.25,
          dashArray: '4, 4'
        };
      },
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        
        layer.on({
          mouseover: (e) => {
            const target = e.target;
            target.setStyle({
              weight: 3.5,
              fillOpacity: 0.45,
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
          <div style="font-family: 'Inter', sans-serif; color: #1e293b; padding: 4px;">
            <strong style="font-size: 14px; color: #0f172a;">${p.name}</strong><br/>
            <span style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600;">Type: ${p.region_type}</span>
            <hr style="margin: 6px 0; border: none; border-top: 1px solid #e2e8f0;"/>
            <div style="font-size: 12px; line-height: 1.5;">
              <div>• <b>Area:</b> ${p.area_sq_km.toLocaleString()} km²</div>
              <div>• <b>Observations:</b> ${p.observation_count}</div>
              <div>• <b>Detected Changes:</b> ${p.change_events_count}</div>
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
    const res = await fetch('/api/spatial/observations?limit=30');
    if (!res.ok) throw new Error('Failed to load observation footprints');
    const geojsonData = await res.json();

    if (footprintsLayer && mapInstance) {
      mapInstance.removeLayer(footprintsLayer);
    }

    footprintsLayer = L.geoJSON(geojsonData, {
      style: () => ({
        color: '#38bdf8',
        weight: 1,
        opacity: 0.6,
        fillColor: '#0284c7',
        fillOpacity: 0.08
      }),
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        layer.bindPopup(`
          <div style="font-family: 'Inter', sans-serif; color: #1e293b; padding: 4px;">
            <strong style="font-size: 13px;">Footprint: ${p.image_reference}</strong><br/>
            <span style="font-size: 11px; color: #64748b;">${p.satellite_name} (${p.sensor_name})</span>
            <hr style="margin: 4px 0; border: none; border-top: 1px solid #e2e8f0;"/>
            <div style="font-size: 11px;">
              <div>Date: ${p.observation_date}</div>
              <div>Resolution: ${p.resolution_m}m</div>
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

  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
      <h4 style="font-size: 15px; color: #ffffff; font-weight: 600;">${p.name}</h4>
      <span class="badge ${p.region_type}">${p.region_type}</span>
    </div>
    <div style="color: var(--text-dim); font-size: 12px; margin-bottom: 8px;">
      PostGIS Polygon (SRID: 4326 WGS84)
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
      <div style="background: rgba(255,255,255,0.03); padding: 8px; border-radius: 4px;">
        <span style="color: var(--text-muted); display: block; font-size: 10px; text-transform: uppercase;">Surface Area</span>
        <strong style="font-size: 14px; color: #ffffff;">${p.area_sq_km.toLocaleString()} km²</strong>
      </div>
      <div style="background: rgba(255,255,255,0.03); padding: 8px; border-radius: 4px;">
        <span style="color: var(--text-muted); display: block; font-size: 10px; text-transform: uppercase;">Observations</span>
        <strong style="font-size: 14px; color: var(--accent-cyan);">${p.observation_count} Passes</strong>
      </div>
    </div>
    <div style="margin-top: 8px; font-size: 11px; color: var(--text-muted);">
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
