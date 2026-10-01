/**
 * sql_console.js - Interactive SQL Query Console & Viva Demonstration Runner
 */

let presetQueriesList = [];

async function initSqlConsole() {
  await loadPresetQueries();
  setupSqlEventListeners();
}

async function loadPresetQueries() {
  const container = document.getElementById('preset-queries-container');
  if (!container) return;

  try {
    const res = await fetch('/api/sql/viva-queries');
    presetQueriesList = await res.json();

    container.innerHTML = presetQueriesList.map((q, idx) => `
      <div class="preset-card ${idx === 0 ? 'active' : ''}" data-id="${q.id}" onclick="selectPresetQuery('${q.id}')">
        <div class="preset-tag">${q.category}</div>
        <div class="preset-title">${q.title}</div>
        <div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">
          ${q.description.substring(0, 75)}...
        </div>
      </div>
    `).join('');

    if (presetQueriesList.length > 0) {
      selectPresetQuery(presetQueriesList[0].id);
    }
  } catch (err) {
    console.error('Error loading preset queries:', err);
  }
}

function selectPresetQuery(queryId) {
  const q = presetQueriesList.find(item => item.id === queryId);
  if (!q) return;

  // Highlight card
  document.querySelectorAll('.preset-card').forEach(card => {
    card.classList.toggle('active', card.dataset.id === queryId);
  });

  const textarea = document.getElementById('sql-query-input');
  if (textarea) textarea.value = q.sql;

  const descEl = document.getElementById('active-query-description');
  if (descEl) descEl.textContent = q.description;
}

function setupSqlEventListeners() {
  const runBtn = document.getElementById('run-sql-btn');
  const explainBtn = document.getElementById('run-explain-btn');

  if (runBtn) {
    runBtn.addEventListener('click', () => runSqlQuery(false));
  }
  if (explainBtn) {
    explainBtn.addEventListener('click', () => runSqlQuery(true));
  }
}

async function runSqlQuery(explain = false) {
  const textarea = document.getElementById('sql-query-input');
  const query = textarea?.value?.trim();
  if (!query) return;

  const latencyBadge = document.getElementById('sql-latency-badge');
  const countBadge = document.getElementById('sql-count-badge');
  const resultsContainer = document.getElementById('sql-results-table-container');
  const explainContainer = document.getElementById('sql-explain-container');

  if (latencyBadge) latencyBadge.textContent = 'Executing...';
  if (explainContainer) explainContainer.style.display = 'none';

  try {
    const res = await fetch('/api/sql/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, explain: explain })
    });

    const data = await res.json();

    if (!data.success) {
      if (latencyBadge) latencyBadge.textContent = 'Error';
      resultsContainer.innerHTML = `
        <div style="padding: 16px; background: rgba(244, 63, 94, 0.1); border: 1px solid var(--accent-rose); border-radius: 6px; color: #fca5a5;">
          <strong>Database Execution Error:</strong><br/>
          <pre style="margin-top: 6px; font-family: monospace; white-space: pre-wrap;">${data.error}</pre>
        </div>
      `;
      return;
    }

    if (latencyBadge) latencyBadge.textContent = `⚡ ${data.execution_time_ms} ms`;
    if (countBadge) countBadge.textContent = `${data.row_count} row(s)`;

    // Render explain plan if present
    if (data.explain_plan && data.explain_plan.length > 0) {
      explainContainer.style.display = 'block';
      explainContainer.innerHTML = `<strong>Query Execution Plan (EXPLAIN ANALYZE):</strong><br/><br/>` + 
        data.explain_plan.join('\n');
    }

    // Render Table
    if (data.columns && data.columns.length > 0) {
      const thead = `<tr>${data.columns.map(c => `<th>${c}</th>`).join('')}</tr>`;
      const tbody = data.rows.map(row => {
        return `<tr>${data.columns.map(col => {
          let val = row[col];
          if (val === null || val === undefined) val = '<span style="color:#64748b">NULL</span>';
          return `<td>${val}</td>`;
        }).join('')}</tr>`;
      }).join('');

      resultsContainer.innerHTML = `
        <div class="data-table-wrapper" style="max-height: 400px; overflow-y: auto;">
          <table class="data-table">
            <thead>${thead}</thead>
            <tbody>${tbody}</tbody>
          </table>
        </div>
      `;
    } else {
      resultsContainer.innerHTML = `<div style="padding: 16px; color: var(--text-dim);">Query executed successfully with 0 result columns.</div>`;
    }

  } catch (err) {
    if (latencyBadge) latencyBadge.textContent = 'Error';
    resultsContainer.innerHTML = `<div style="padding: 16px; color: var(--accent-rose);">Network error: ${err.message}</div>`;
  }
}
