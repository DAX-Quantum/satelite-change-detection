/**
 * app.js - Main Application Orchestrator
 * Handles Tab Navigation, Global Stats, Change Detection Controller, and Architecture Inspector
 */

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  loadGlobalStats();
  initMap();
  initAllCharts();
  initChangeDetectionTab();
  initArchitectureTab();
  initSqlConsole();
});

// Tab Navigation
function initNavigation() {
  const navButtons = document.querySelectorAll('.nav-item button');
  const tabPanels = document.querySelectorAll('.tab-content');

  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabTarget = btn.dataset.tab;

      navButtons.forEach(b => b.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const activePanel = document.getElementById(`tab-${tabTarget}`);
      if (activePanel) {
        activePanel.classList.add('active');
      }

      // Special triggers on tab open
      if (tabTarget === 'map') {
        resizeMap();
      } else if (tabTarget === 'analytics') {
        initAllCharts();
      }
    });
  });
}

// Global System Statistics
async function loadGlobalStats() {
  try {
    const res = await fetch('/api/stats/overview');
    if (!res.ok) throw new Error('Failed to load stats');
    const stats = await res.json();

    document.getElementById('stat-satellites').textContent = stats.satellites_count;
    document.getElementById('stat-regions').textContent = stats.regions_count;
    document.getElementById('stat-observations').textContent = stats.observations_count;
    document.getElementById('stat-fact-rows').textContent = stats.fact_observations_count.toLocaleString();
    document.getElementById('stat-changed-area').textContent = `${stats.total_changed_area_sq_km || 0} km²`;
    document.getElementById('db-size-label').textContent = stats.database_size;
  } catch (err) {
    console.error('Error loading global stats:', err);
  }
}

// Change Detection Controller
async function initChangeDetectionTab() {
  await loadChangeEventsTable();
  await populateCompareDropdowns();
  setupCompareAction();
}

async function loadChangeEventsTable() {
  const container = document.getElementById('change-events-table-body');
  if (!container) return;

  try {
    const res = await fetch('/api/changes/events');
    const events = await res.json();

    container.innerHTML = events.map(ev => `
      <tr>
        <td><strong>#${ev.change_id}</strong></td>
        <td><b>${ev.region_name}</b> <span class="badge ${ev.region_type}">${ev.region_type}</span></td>
        <td><span class="badge ${ev.from_land_cover.toLowerCase()}">${ev.from_land_cover}</span></td>
        <td>➔ <span class="badge ${ev.to_land_cover.toLowerCase()}">${ev.to_land_cover}</span></td>
        <td>${ev.start_date} to ${ev.end_date}</td>
        <td>${ev.duration_days} days</td>
        <td style="color: var(--accent-rose); font-weight: 600;">${ev.changed_area_sq_km.toLocaleString()} km²</td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading change events:', err);
  }
}

async function populateCompareDropdowns() {
  const regionSelect = document.getElementById('compare-region-select');
  if (!regionSelect) return;

  try {
    const res = await fetch('/api/spatial/regions');
    const geojson = await res.json();

    regionSelect.innerHTML = geojson.features.map(f => `
      <option value="${f.properties.region_id}">${f.properties.name}</option>
    `).join('');

    regionSelect.addEventListener('change', updateAvailableDatesForRegion);
    await updateAvailableDatesForRegion();
  } catch (err) {
    console.error('Error populating compare dropdowns:', err);
  }
}

async function updateAvailableDatesForRegion() {
  const regionId = document.getElementById('compare-region-select').value;
  const startSelect = document.getElementById('compare-date-start');
  const endSelect = document.getElementById('compare-date-end');
  if (!startSelect || !endSelect) return;

  try {
    const res = await fetch(`/api/changes/available-dates?region_id=${regionId}`);
    const dates = await res.json();

    if (dates.length > 0) {
      startSelect.innerHTML = dates.map(d => `<option value="${d}">${d}</option>`).join('');
      endSelect.innerHTML = dates.map(d => `<option value="${d}">${d}</option>`).join('');

      // Set defaults: first date and last date
      startSelect.value = dates[0];
      endSelect.value = dates[dates.length - 1];
    }
  } catch (err) {
    console.error('Error updating dates:', err);
  }
}

function setupCompareAction() {
  const compareBtn = document.getElementById('run-compare-btn');
  if (compareBtn) {
    compareBtn.addEventListener('click', triggerComparison);
  }
  window.triggerComparison = triggerComparison;
}

async function triggerComparison() {
  const regionId = document.getElementById('compare-region-select')?.value;
  const dateStart = document.getElementById('compare-date-start')?.value;
  const dateEnd = document.getElementById('compare-date-end')?.value;
  const resultsContainer = document.getElementById('compare-results-container');
  if (!resultsContainer) return;

  resultsContainer.innerHTML = `<div style="padding: 20px; color: var(--text-dim);">Calling operational.fn_compare_landcover()...</div>`;

  try {
    const res = await fetch(`/api/changes/compare?region_id=${regionId}&date_start=${dateStart}&date_end=${dateEnd}`);
    const data = await res.json();

    const shifts = data.shifts || [];
    const rowsHtml = shifts.map(s => {
      const isPositive = s.net_change_sq_km > 0;
      const badgeClass = isPositive ? 'badge positive' : 'badge negative';
      const sign = isPositive ? '+' : '';
      return `
        <tr>
          <td><span class="badge ${s.land_cover_name.toLowerCase()}">${s.land_cover_name}</span></td>
          <td>${s.initial_area_sq_km.toLocaleString()} km²</td>
          <td>${s.final_area_sq_km.toLocaleString()} km²</td>
          <td class="${badgeClass}">${sign}${s.net_change_sq_km} km²</td>
          <td class="${badgeClass}">${sign}${s.change_pct}%</td>
        </tr>
      `;
    }).join('');

    resultsContainer.innerHTML = `
      <div class="data-table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Land Cover Type</th>
              <th>Initial Area (${dateStart})</th>
              <th>Final Area (${dateEnd})</th>
              <th>Net Shift</th>
              <th>Change (%)</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;

    // Also update the stacked chart for this region
    renderLandCoverCompositionChart(regionId);

  } catch (err) {
    console.error('Error comparing land cover:', err);
    resultsContainer.innerHTML = `<div style="color: var(--accent-rose);">Error executing comparison: ${err.message}</div>`;
  }
}

// Architecture & ERD Inspector
async function initArchitectureTab() {
  const container = document.getElementById('schema-tables-grid');
  if (!container) return;

  try {
    const res = await fetch('/api/stats/schemas');
    const tables = await res.json();

    container.innerHTML = tables.map(tbl => {
      const isWarehouse = tbl.schema === 'warehouse';
      const isFact = tbl.table_name.startsWith('fact');
      const cardClass = isFact ? 'fact-erd' : (isWarehouse ? 'warehouse-erd' : '');

      const colList = tbl.columns.map(c => {
        let flagClass = '';
        let flagText = '';
        if (c.column_name.includes('_id') || c.column_name.includes('_key')) {
          flagClass = c.column_name.endsWith('_key') ? 'fk' : 'pk';
          flagText = c.column_name.endsWith('_key') ? 'KEY' : 'ID';
        } else if (c.data_type === 'USER-DEFINED') {
          flagClass = 'geom';
          flagText = 'GEOM';
        }
        return `
          <li class="erd-col-item">
            <span class="erd-col-name ${flagClass}">${c.column_name}</span>
            <span class="erd-col-type">${flagText || c.data_type}</span>
          </li>
        `;
      }).join('');

      return `
        <div class="erd-card ${cardClass}">
          <h4>
            <span><b>${tbl.schema}.</b>${tbl.table_name}</span>
            <span class="badge" style="background: rgba(255,255,255,0.06);">${tbl.row_count} rows</span>
          </h4>
          <ul class="erd-columns-list">
            ${colList}
          </ul>
        </div>
      `;
    }).join('');

  } catch (err) {
    console.error('Error loading schema tables:', err);
  }
}
