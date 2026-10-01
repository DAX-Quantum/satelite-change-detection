/**
 * charts.js - Chart.js Visualizations for Data Warehouse Analytics & OLAP
 */

let landCoverChartInstance = null;
let urbanTrendChartInstance = null;
let sensorVolumeChartInstance = null;
let deforestationChartInstance = null;

// Global theme options for Chart.js
const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: '#94a3b8',
        font: { family: "'Inter', sans-serif", size: 11 }
      }
    },
    tooltip: {
      backgroundColor: 'rgba(7, 11, 20, 0.95)',
      titleColor: '#ffffff',
      bodyColor: '#e2e8f0',
      borderColor: 'rgba(56, 189, 248, 0.3)',
      borderWidth: 1,
      padding: 10,
      cornerRadius: 6,
      bodyFont: { family: "'Inter', sans-serif" }
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(255, 255, 255, 0.05)' },
      ticks: { color: '#64748b', font: { family: "'Inter', sans-serif", size: 11 } }
    },
    y: {
      grid: { color: 'rgba(255, 255, 255, 0.05)' },
      ticks: { color: '#64748b', font: { family: "'Inter', sans-serif", size: 11 } }
    }
  }
};

async function initAllCharts() {
  await renderUrbanTrendChart();
  await renderLandCoverCompositionChart();
  await renderSensorVolumeChart();
  await renderDeforestationChart();
}

async function renderUrbanTrendChart() {
  const ctx = document.getElementById('urban-trend-chart')?.getContext('2d');
  if (!ctx) return;

  try {
    const res = await fetch('/api/warehouse/urban-expansion');
    const data = await res.json();

    // Group periods and series by region
    const periods = [...new Set(data.map(d => d.period))];
    const regions = ['Delhi NCR', 'Mumbai Metropolitan', 'Bengaluru Urban'];
    const colors = {
      'Delhi NCR': '#38bdf8',          // Cyan
      'Mumbai Metropolitan': '#f43f5e', // Rose
      'Bengaluru Urban': '#a855f7'      // Purple
    };

    const datasets = regions.map(reg => {
      const regData = data.filter(d => d.region_name === reg);
      return {
        label: reg + ' (Rolling 3Q Avg)',
        data: regData.map(d => d.rolling_3q_avg_sq_km),
        borderColor: colors[reg],
        backgroundColor: colors[reg] + '20',
        fill: false,
        tension: 0.35,
        borderWidth: 2.5,
        pointRadius: 3
      };
    });

    if (urbanTrendChartInstance) urbanTrendChartInstance.destroy();

    urbanTrendChartInstance = new Chart(ctx, {
      type: 'line',
      data: { labels: periods, datasets: datasets },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          title: { display: false }
        },
        scales: {
          ...CHART_DEFAULTS.scales,
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Urban Area (km²)', color: '#94a3b8' }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error rendering urban chart:', err);
  }
}

async function renderLandCoverCompositionChart(regionId = 1) {
  const ctx = document.getElementById('landcover-stacked-chart')?.getContext('2d');
  if (!ctx) return;

  try {
    const res = await fetch(`/api/warehouse/quarterly-trends?region_id=${regionId}`);
    const data = await res.json();

    const periods = [...new Set(data.map(d => d.period_label))];
    const landCovers = ['Urban', 'Forest', 'Agriculture', 'Water', 'Barren'];
    const lcColors = {
      'Urban': '#f43f5e',
      'Forest': '#10b981',
      'Agriculture': '#f59e0b',
      'Water': '#06b6d4',
      'Barren': '#a855f7'
    };

    const datasets = landCovers.map(lc => {
      const filtered = data.filter(d => d.land_cover_name === lc);
      return {
        label: lc,
        data: filtered.map(d => d.total_area_sq_km),
        backgroundColor: lcColors[lc] || '#94a3b8',
        borderRadius: 2
      };
    });

    if (landCoverChartInstance) landCoverChartInstance.destroy();

    landCoverChartInstance = new Chart(ctx, {
      type: 'bar',
      data: { labels: periods, datasets: datasets },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          x: { ...CHART_DEFAULTS.scales.x, stacked: true },
          y: {
            ...CHART_DEFAULTS.scales.y,
            stacked: true,
            title: { display: true, text: 'Total Area (km²)', color: '#94a3b8' }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error rendering land cover chart:', err);
  }
}

async function renderSensorVolumeChart() {
  const ctx = document.getElementById('sensor-volume-chart')?.getContext('2d');
  if (!ctx) return;

  try {
    const res = await fetch('/api/warehouse/sensor-metrics');
    const data = await res.json();

    const labels = data.map(d => `${d.satellite_name} (${d.sensor_name})`);
    const areaValues = data.map(d => d.total_area_sq_km);

    if (sensorVolumeChartInstance) sensorVolumeChartInstance.destroy();

    sensorVolumeChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Total Surveyed Area (km²)',
          data: areaValues,
          backgroundColor: 'rgba(6, 182, 212, 0.7)',
          borderColor: '#06b6d4',
          borderWidth: 1,
          borderRadius: 4
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        indexAxis: 'y',
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false }
        },
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: { display: true, text: 'Square Kilometers Observed', color: '#94a3b8' }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error rendering sensor chart:', err);
  }
}

async function renderDeforestationChart() {
  const ctx = document.getElementById('deforestation-chart')?.getContext('2d');
  if (!ctx) return;

  try {
    const res = await fetch('/api/warehouse/deforestation-index');
    const data = await res.json();

    // Filter only rows with non-null annual_loss
    const validDeltas = data.filter(d => d.annual_loss_sq_km !== null);
    const labels = validDeltas.map(d => `${d.region_name} (${d.year})`);
    const deltas = validDeltas.map(d => d.annual_loss_sq_km);
    const barColors = deltas.map(v => v < 0 ? 'rgba(244, 63, 94, 0.75)' : 'rgba(16, 185, 129, 0.75)');

    if (deforestationChartInstance) deforestationChartInstance.destroy();

    deforestationChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Net Annual Forest Delta (km²)',
          data: deltas,
          backgroundColor: barColors,
          borderRadius: 4
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false }
        },
        scales: {
          ...CHART_DEFAULTS.scales,
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Net Area Delta (km²)', color: '#94a3b8' }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error rendering deforestation chart:', err);
  }
}
