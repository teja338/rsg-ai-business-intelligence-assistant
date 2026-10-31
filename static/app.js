let chart = null;
let currentTableData = null;
let currentChartData = {
  monthly: null,
  categories: null,
  channels: null,
  regions: null
};

const money = value => new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2
}).format(Number(value || 0));

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    ...options
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.detail || 'Request failed');
  }
  return body;
}

function renderData(data) {
  const target = document.getElementById('supportingData');
  const exportBtn = document.getElementById('exportCsvBtn');
  target.innerHTML = '';
  currentTableData = data;

  if (Array.isArray(data) && data.length) {
    exportBtn.style.display = 'inline-block';
    const keys = Object.keys(data[0]);
    const table = document.createElement('table');
    table.className = 'data-table';
    table.innerHTML = (
      '<thead><tr>' +
      keys.map(k => `<th>${k.replaceAll('_', ' ').toUpperCase()}</th>`).join('') +
      '</tr></thead><tbody>' +
      data.map(row => (
        '<tr>' +
        keys.map(k => {
          const val = row[k];
          if (typeof val === 'number' && (k.includes('revenue') || k === 'change' || k.includes('price'))) {
            return `<td><strong>${money(val)}</strong></td>`;
          }
          return `<td>${val === null || val === undefined ? '—' : String(val)}</td>`;
        }).join('') +
        '</tr>'
      )).join('') +
      '</tbody>'
    );
    target.appendChild(table);
  } else if (data && typeof data === 'object') {
    exportBtn.style.display = 'inline-block';
    const entries = Object.entries(data);
    const table = document.createElement('table');
    table.className = 'data-table';
    table.innerHTML = (
      '<tbody>' +
      entries.map(([k, v]) => {
        let formatted = v === null || v === undefined ? '—' : String(v);
        if (typeof v === 'number' && (k.includes('revenue') || k === 'change' || k.includes('price'))) {
          formatted = `<strong>${money(v)}</strong>`;
        }
        return `<tr><th>${k.replaceAll('_', ' ').toUpperCase()}</th><td>${formatted}</td></tr>`;
      }).join('') +
      '</tbody>'
    );
    target.appendChild(table);
  } else {
    exportBtn.style.display = 'none';
  }
}

function exportCsv() {
  if (!currentTableData) return;
  let rows = [];
  if (Array.isArray(currentTableData) && currentTableData.length) {
    const keys = Object.keys(currentTableData[0]);
    rows.push(keys.join(','));
    currentTableData.forEach(item => {
      rows.push(keys.map(k => `"${String(item[k] ?? '').replace(/"/g, '""')}"`).join(','));
    });
  } else if (typeof currentTableData === 'object') {
    rows.push('Metric,Value');
    Object.entries(currentTableData).forEach(([k, v]) => {
      rows.push(`"${k}","${String(v ?? '').replace(/"/g, '""')}"`);
    });
  }
  const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `sales_analysis_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function showResult(result) {
  const box = document.getElementById('result');
  box.classList.remove('hidden');
  document.getElementById('answerText').textContent = result.answer;
  const tag = document.getElementById('methodTag');
  tag.textContent = result.interpretation_method === 'llm' ? '🤖 AI Interpreted' : '⚡ Deterministic Rules';

  const sqlContainer = document.getElementById('sqlContainer');
  const sqlCode = document.getElementById('sqlCode');
  if (result.sql) {
    sqlContainer.style.display = 'block';
    sqlCode.textContent = result.sql;
  } else {
    sqlContainer.style.display = 'none';
  }

  renderData(result.data);
  box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function ask(question) {
  const button = document.getElementById('askButton');
  button.disabled = true;
  button.textContent = 'Thinking…';
  try {
    const result = await api('/api/ask', {
      method: 'POST',
      body: JSON.stringify({ question })
    });
    showResult(result);
  } catch (error) {
    showResult({
      answer: error.message,
      data: null,
      interpretation_method: 'error'
    });
  } finally {
    button.disabled = false;
    button.innerHTML = 'Ask assistant <span>→</span>';
  }
}

async function updateChart(viewType) {
  const ctx = document.getElementById('revenueChart');
  const title = document.getElementById('chartTitle');
  const subtitle = document.getElementById('chartSubtitle');
  const range = document.getElementById('chartRange');

  document.querySelectorAll('.chart-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.view === viewType);
  });

  let labels = [];
  let dataPoints = [];
  let chartType = 'bar';
  let colors = ['#3b68df', '#28a745', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4'];

  if (viewType === 'monthly') {
    title.textContent = 'Monthly Revenue Trend';
    subtitle.textContent = 'Net revenue by order month';
    range.textContent = 'Jan – Jun 2026';
    if (!currentChartData.monthly) {
      const res = await api('/api/ask', { method: 'POST', body: JSON.stringify({ question: 'Show monthly revenue trend' }) });
      currentChartData.monthly = res.data || [];
    }
    labels = currentChartData.monthly.map(r => r.month);
    dataPoints = currentChartData.monthly.map(r => r.revenue);
  } else if (viewType === 'categories') {
    title.textContent = 'Revenue by Product Category';
    subtitle.textContent = 'Accessories, Electronics & Furniture';
    range.textContent = 'Total Period';
    if (!currentChartData.categories) {
      const res = await api('/api/categories');
      currentChartData.categories = res.data || [];
    }
    labels = currentChartData.categories.map(r => r.category);
    dataPoints = currentChartData.categories.map(r => r.revenue);
  } else if (viewType === 'channels') {
    title.textContent = 'Sales Channel Distribution';
    subtitle.textContent = 'Online vs. Retail Sales Volume & Value';
    range.textContent = 'Total Period';
    if (!currentChartData.channels) {
      const res = await api('/api/channels');
      currentChartData.channels = res.data || [];
    }
    labels = currentChartData.channels.map(r => r.sales_channel);
    dataPoints = currentChartData.channels.map(r => r.revenue);
  } else if (viewType === 'regions') {
    title.textContent = 'Territory Performance';
    subtitle.textContent = 'Sales revenue across South, North, East & West';
    range.textContent = 'Total Period';
    if (!currentChartData.regions) {
      const res = await api('/api/ask', { method: 'POST', body: JSON.stringify({ question: 'Show sales by all regions' }) });
      currentChartData.regions = res.data || [];
    }
    labels = currentChartData.regions.map(r => r.region);
    dataPoints = currentChartData.regions.map(r => r.revenue);
  }

  if (chart) chart.destroy();

  chart = new Chart(ctx, {
    type: chartType,
    data: {
      labels: labels,
      datasets: [{
        label: 'Net Revenue',
        data: dataPoints,
        backgroundColor: colors.slice(0, labels.length),
        borderRadius: 6,
        maxBarThickness: 32
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: c => money(c.raw)
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', font: { size: 11, weight: '500' } }
        },
        y: {
          beginAtZero: true,
          grid: { color: '#e2e8f0' },
          ticks: {
            color: '#64748b',
            font: { size: 10 },
            callback: v => '₹' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v)
          }
        }
      }
    }
  });
}

async function loadDashboard() {
  try {
    const s = await api('/api/summary');
    document.getElementById('totalRows').textContent = s.total_rows ?? 0;
    document.getElementById('eligibleRows').textContent = s.eligible_rows ?? 0;
    document.getElementById('excludedRows').textContent = s.excluded_rows ?? 0;
    
    // Clear cached chart data for clean reload
    currentChartData = { monthly: null, categories: null, channels: null, regions: null };
    await updateChart('monthly');
  } catch (e) {
    console.error('Failed to load dashboard metrics:', e);
  }
}

// Event Listeners
document.getElementById('askForm').addEventListener('submit', e => {
  e.preventDefault();
  const q = document.getElementById('question').value.trim();
  if (q) ask(q);
});

document.querySelectorAll('.suggestion').forEach(btn => {
  btn.addEventListener('click', () => {
    const q = btn.dataset.q;
    document.getElementById('question').value = q;
    ask(q);
  });
});

document.querySelectorAll('.chart-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    updateChart(tab.dataset.view);
  });
});

document.getElementById('exportCsvBtn').addEventListener('click', exportCsv);

document.getElementById('copySqlBtn').addEventListener('click', () => {
  const sql = document.getElementById('sqlCode').textContent;
  if (sql) {
    navigator.clipboard.writeText(sql);
    const btn = document.getElementById('copySqlBtn');
    btn.textContent = '✓ Copied!';
    setTimeout(() => { btn.textContent = '📋 Copy SQL'; }, 2000);
  }
});

document.getElementById('excludedCard').addEventListener('click', () => {
  const q = 'Why were records excluded?';
  document.getElementById('question').value = q;
  ask(q);
});

document.getElementById('reloadButton').addEventListener('click', async () => {
  const status = document.getElementById('reloadStatus');
  status.textContent = 'Reloading…';
  try {
    const r = await api('/api/reload', { method: 'POST' });
    status.textContent = `Reloaded ${r.rows_loaded} rows (${r.eligible_rows} eligible)`;
    await loadDashboard();
  } catch (e) {
    status.textContent = 'Error: ' + e.message;
  }
});

const fileInput = document.getElementById('csvFileInput');
const uploadBtn = document.getElementById('uploadButton');

uploadBtn.addEventListener('click', () => {
  fileInput.click();
});

fileInput.addEventListener('change', async () => {
  if (!fileInput.files.length) return;
  const file = fileInput.files[0];
  const status = document.getElementById('reloadStatus');
  status.textContent = `Uploading ${file.name}…`;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await api('/api/upload', {
      method: 'POST',
      body: formData
    });
    status.textContent = `Uploaded ${file.name}: ${res.rows_loaded} rows (${res.eligible_rows} eligible)`;
    await loadDashboard();
  } catch (err) {
    status.textContent = 'Upload failed: ' + err.message;
  } finally {
    fileInput.value = '';
  }
});

// Initialize dashboard on page load
loadDashboard();
