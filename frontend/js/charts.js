/**
 * charts.js - Vibrant Chart.js Visualizations for Data Warehouse Analytics & OLAP
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
        color: '#e2e8f0',
        font: { family: "'Inter', sans-serif", size: 12, weight: '600' },
        usePointStyle: true,
        pointStyle: 'circle',
        padding: 16
      }
    },
    tooltip: {
      backgroundColor: 'rgba(6, 10, 24, 0.95)',
      titleColor: '#00f2fe',
      titleFont: { family: "'Outfit', sans-serif", size: 13, weight: '700' },
      bodyColor: '#f8fafc',
      borderColor: 'rgba(0, 242, 254, 0.4)',
      borderWidth: 1.5,
      padding: 12,
      cornerRadius: 8,
      boxPadding: 6,
      bodyFont: { family: "'Inter', sans-serif", size: 12 },
      displayColors: true
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(255, 255, 255, 0.06)' },
      ticks: { color: '#94a3b8', font: { family: "'Inter', sans-serif", size: 11, weight: '500' } }
    },
    y: {
      grid: { color: 'rgba(255, 255, 255, 0.06)' },
      ticks: { color: '#94a3b8', font: { family: "'Inter', sans-serif", size: 11, weight: '500' } }
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
      'Delhi NCR': { stroke: '#00f2fe', fillStart: 'rgba(0, 242, 254, 0.25)', fillEnd: 'rgba(0, 242, 254, 0.0)' },
      'Mumbai Metropolitan': { stroke: '#f43f5e', fillStart: 'rgba(244, 63, 94, 0.25)', fillEnd: 'rgba(244, 63, 94, 0.0)' },
      'Bengaluru Urban': { stroke: '#a855f7', fillStart: 'rgba(168, 85, 247, 0.25)', fillEnd: 'rgba(168, 85, 247, 0.0)' }
    };

    const datasets = regions.map(reg => {
      const regData = data.filter(d => d.region_name === reg);
      const conf = colors[reg];
      
      const grad = ctx.createLinearGradient(0, 0, 0, 250);
      grad.addColorStop(0, conf.fillStart);
      grad.addColorStop(1, conf.fillEnd);

      return {
        label: reg + ' (Rolling 3Q Avg)',
        data: regData.map(d => d.rolling_3q_avg_sq_km),
        borderColor: conf.stroke,
        backgroundColor: grad,
        fill: true,
        tension: 0.38,
        borderWidth: 3,
        pointBackgroundColor: '#ffffff',
        pointBorderColor: conf.stroke,
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 7
      };
    });

    if (urbanTrendChartInstance) urbanTrendChartInstance.destroy();

    urbanTrendChartInstance = new Chart(ctx, {
      type: 'line',
      data: { labels: periods, datasets: datasets },
      options: {
        ...CHART_DEFAULTS,
        interaction: { mode: 'index', intersect: false },
        scales: {
          ...CHART_DEFAULTS.scales,
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Urban Footprint (km²)', color: '#38bdf8', font: { weight: '600' } }
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
      'Urban': { bg: 'rgba(244, 63, 94, 0.85)', border: '#f43f5e' },
      'Forest': { bg: 'rgba(16, 185, 129, 0.85)', border: '#10b981' },
      'Agriculture': { bg: 'rgba(251, 191, 36, 0.85)', border: '#fbbf24' },
      'Water': { bg: 'rgba(0, 242, 254, 0.85)', border: '#00f2fe' },
      'Barren': { bg: 'rgba(249, 115, 22, 0.85)', border: '#f97316' }
    };

    const datasets = landCovers.map(lc => {
      const filtered = data.filter(d => d.land_cover_name === lc);
      const styling = lcColors[lc] || { bg: 'rgba(148, 163, 184, 0.8)', border: '#94a3b8' };
      return {
        label: lc,
        data: filtered.map(d => d.total_area_sq_km),
        backgroundColor: styling.bg,
        borderColor: styling.border,
        borderWidth: 1,
        borderRadius: 4
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
            title: { display: true, text: 'Total Area (km²)', color: '#c084fc', font: { weight: '600' } }
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
    
    // Multi-color palette distinguishing Optical from Radar
    const bgColors = data.map(d => 
      d.sensor_type?.toLowerCase().includes('radar') 
        ? 'rgba(168, 85, 247, 0.85)' 
        : 'rgba(0, 242, 254, 0.85)'
    );
    const borderColors = data.map(d => 
      d.sensor_type?.toLowerCase().includes('radar') ? '#c084fc' : '#38bdf8'
    );

    if (sensorVolumeChartInstance) sensorVolumeChartInstance.destroy();

    sensorVolumeChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Total Surveyed Area (km²)',
          data: areaValues,
          backgroundColor: bgColors,
          borderColor: borderColors,
          borderWidth: 1.5,
          borderRadius: 6
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
            title: { display: true, text: 'Square Kilometers Observed', color: '#00f2fe', font: { weight: '600' } }
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
    
    // Vibrant Green for positive preservation, Vibrant Rose/Red for forest loss
    const barColors = deltas.map(v => v < 0 ? 'rgba(244, 63, 94, 0.85)' : 'rgba(0, 245, 160, 0.85)');
    const borderColors = deltas.map(v => v < 0 ? '#f43f5e' : '#00f5a0');

    if (deforestationChartInstance) deforestationChartInstance.destroy();

    deforestationChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Net Annual Forest Delta (km²)',
          data: deltas,
          backgroundColor: barColors,
          borderColor: borderColors,
          borderWidth: 1.5,
          borderRadius: 6
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { display: false }
        },
        scales: {
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: { display: true, text: 'Net Area Delta (km²)', color: '#00f5a0', font: { weight: '600' } }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error rendering deforestation chart:', err);
  }
}
