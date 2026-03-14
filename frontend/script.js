// ============================================================
//  Smart Traffic Flow Optimizer — Dashboard Script
// ============================================================

const API = {
  traffic:   'http://127.0.0.1:5000/traffic',
  route:     (s, e) => `http://127.0.0.1:5000/route/${encodeURIComponent(s)}/${encodeURIComponent(e)}`,
  schedule:  'http://127.0.0.1:5000/schedule',
  emergency: 'http://127.0.0.1:5000/emergency',
  predict:   road => `http://127.0.0.1:5000/predict/${encodeURIComponent(road)}`,
};

// ── State ────────────────────────────────────────────────────
let trafficData    = [];
let chartInstance  = null;
let mapSvg         = null;

// ── Utilities ────────────────────────────────────────────────
const el  = id => document.getElementById(id);
const fmt = n  => Number(n).toLocaleString();

function loading(id, msg = 'Loading…') {
  el(id).innerHTML = `<div class="loader"><div class="spinner"></div>${msg}</div>`;
}

function errMsg(id, msg = 'Failed to load data.') {
  el(id).innerHTML = `<div class="error-msg">⚠ ${msg}</div>`;
}

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── 1. Traffic Data ──────────────────────────────────────────
async function loadTraffic() {
  loading('traffic-table-body', '');
  loading('kpi-total-vehicles', '');
  loading('kpi-status-area', '');

  try {
    const data = await fetchJSON(API.traffic);
    // Normalise: accept array or { roads: [...] } or object map
    if (Array.isArray(data)) {
      trafficData = data;
    } else if (data.roads) {
      trafficData = data.roads;
    } else {
      // object of road → info
      trafficData = Object.entries(data).map(([road, info]) => ({
        road,
        ...info,
      }));
    }

    renderKPI();
    renderTrafficTable();
    renderMap();
    renderChart();
    populateRouteSelects();
  } catch (e) {
    errMsg('traffic-table-body', 'Could not fetch traffic data.');
    errMsg('kpi-total-vehicles', '—');
    errMsg('kpi-status-area', '—');
    console.error(e);
  }
}

function renderKPI() {
  // Total vehicles
  const total = trafficData.reduce((s, r) => s + Number(r.vehicle_count ?? r.vehicles ?? 0), 0);
  el('kpi-total-vehicles').textContent = fmt(total);

  // Congested count
  const congested = trafficData.filter(r =>
    (r.congestion_status ?? r.status ?? r.congestion ?? '').toString().toLowerCase().includes('congest')
  ).length;

  const percent = trafficData.length ? Math.round(congested / trafficData.length * 100) : 0;
  const badge   = congested > 0
    ? `<span class="kpi-badge badge-congested">⚠ ${congested} Congested</span>`
    : `<span class="kpi-badge badge-normal">✓ All Clear</span>`;

  el('kpi-status-area').innerHTML = badge;
  el('kpi-congestion-pct').textContent = `${percent}% of roads congested`;
  el('kpi-road-count').textContent = trafficData.length;
}

function renderTrafficTable() {
  const tbody = el('traffic-table-body');
  if (!trafficData.length) { errMsg('traffic-table-body', 'No road data available.'); return; }

  tbody.innerHTML = trafficData.map(r => {
    const road     = r.road ?? r.name ?? '—';
    const vehicles = Number(r.vehicle_count ?? r.vehicles ?? 0);
    const capacity = Number(r.capacity ?? 100);
    const status   = (r.congestion_status ?? r.status ?? r.congestion ?? '').toString();
    const pct      = capacity > 0 ? Math.min(100, Math.round(vehicles / capacity * 100)) : 0;
    const fillClass = pct >= 80 ? 'high' : pct >= 50 ? 'medium' : '';
    const badgeClass = status.toLowerCase().includes('congest') ? 'badge-congested' : 'badge-normal';
    const badgeText  = status.toLowerCase().includes('congest') ? 'Congested' : status || 'Normal';

    return `
      <tr>
        <td><strong>${road}</strong></td>
        <td>${fmt(vehicles)}</td>
        <td>${fmt(capacity)}</td>
        <td>
          <div class="progress-bar">
            <div class="progress-fill ${fillClass}" style="width:${pct}%"></div>
          </div>
        </td>
        <td><span class="kpi-badge ${badgeClass}">${badgeText}</span></td>
      </tr>`;
  }).join('');
}

// ── 2. Route Planner ──────────────────────────────────────────
function populateRouteSelects() {
  const roads = trafficData.map(r => r.road ?? r.name).filter(Boolean);
  ['route-start', 'route-end'].forEach(id => {
    const sel = el(id);
    const cur = sel.value;
    sel.innerHTML = roads.map(r => `<option value="${r}">${r}</option>`).join('');
    if (roads.includes(cur)) sel.value = cur;
  });
}

async function loadRoute() {
  const start = el('route-start').value;
  const end   = el('route-end').value;
  if (!start || !end || start === end) {
    el('route-result').innerHTML = '<p style="color:var(--text-muted);font-size:.8rem">Please select two different roads.</p>';
    return;
  }

  el('route-result').innerHTML = '<div class="loader"><div class="spinner"></div>Finding route…</div>';

  try {
    const data = await fetchJSON(API.route(start, end));
    // Normalise: { path: [...] } or { route: [...] } or array
    const path = data.path ?? data.route ?? (Array.isArray(data) ? data : null);
    const cost = data.cost ?? data.distance ?? data.total_cost ?? null;

    if (!path || !path.length) {
      el('route-result').innerHTML = '<p style="color:var(--text-muted);font-size:.8rem">No route found.</p>';
      return;
    }

    const nodes = path.map((n, i) => {
      const isLast = i === path.length - 1;
      return `<span class="route-node">${n}</span>${isLast ? '' : '<span class="route-arrow">→</span>'}`;
    }).join('');

    el('route-result').innerHTML = `
      <div class="route-path">${nodes}</div>
      ${cost !== null ? `<p class="route-meta">🚦 Traffic cost (lower = less congested): <strong>${cost}</strong></p>` : ''}
    `;
  } catch (e) {
    el('route-result').innerHTML = '<p class="error-msg">⚠ Could not fetch route.</p>';
    console.error(e);
  }
}

// ── 3. Schedule ───────────────────────────────────────────────
async function loadSchedule() {
  loading('schedule-body', 'Loading schedule…');
  try {
    const data = await fetchJSON(API.schedule);
    // Normalise: { batches: [...] } or array or object
    let batches = data.batches ?? data.schedule ?? (Array.isArray(data) ? data : null);
    if (!batches) {
      batches = Object.entries(data).map(([k, v]) => ({ batch: k, ...(typeof v === 'object' ? v : { vehicles: v }) }));
    }

    if (!batches.length) { errMsg('schedule-body', 'No schedule data.'); return; }

    el('schedule-body').innerHTML = batches.map((b, i) => {
      const name       = b.batch ?? b.name ?? b.id ?? `Batch ${i + 1}`;
      const vehicles   = b.vehicle_count ?? b.vehicles ?? b.count ?? '—';
      const road       = b.road ?? b.route ?? b.assigned_road ?? '';
      const time       = b.time ?? b.time_slot ?? b.scheduled_time ?? b.departure ?? '';
      const tokenStart = b.token_start ?? null;
      const tokenEnd   = b.token_end   ?? null;
      const tokenStr   = (tokenStart !== null && tokenEnd !== null)
        ? `🎫 Tokens ${tokenStart}–${tokenEnd}` : '';
      const info = [road && `Road: ${road}`, time && `Time: ${time}`].filter(Boolean).join(' · ');

      return `
        <div class="schedule-item">
          <div>
            <div class="schedule-batch">${name}</div>
            ${info ? `<div class="schedule-info">${info}</div>` : ''}
            ${tokenStr ? `<div class="schedule-info" style="color:#8b5cf6;font-weight:600">${tokenStr}</div>` : ''}
          </div>
          <span class="schedule-count">${fmt(vehicles)} vehicles</span>
        </div>`;
    }).join('');
  } catch (e) {
    errMsg('schedule-body', 'Could not fetch schedule.');
    console.error(e);
  }
}

// ── 4. Emergency ──────────────────────────────────────────────
async function loadEmergency() {
  loading('emergency-body', 'Loading emergency data…');
  try {
    const data = await fetchJSON(API.emergency);
    const path  = data.path ?? data.route ?? data.priority_route ?? (Array.isArray(data) ? data : null);
    const vtype = data.vehicle_type ?? data.type ?? 'Emergency Vehicle';
    const eta   = data.eta ?? data.estimated_time ?? null;

    if (!path || !path.length) {
      el('emergency-body').innerHTML = '<p style="color:var(--text-muted);font-size:.8rem;padding:.5rem">No active emergency routes.</p>';
      return;
    }

    const nodes = path.map((n, i) => {
      const isLast = i === path.length - 1;
      return `<span class="emergency-node">${n}</span>${isLast ? '' : '<span class="emergency-arrow"> → </span>'}`;
    }).join('');

    el('emergency-body').innerHTML = `
      <div class="emergency-alert">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <div class="emergency-info">
          <h4>🚨 ${vtype} Priority Route</h4>
          <div class="emergency-path">${nodes}</div>
          ${eta !== null ? `<p>⏱ Estimated time: <strong>${eta}</strong></p>` : ''}
        </div>
      </div>`;
  } catch (e) {
    errMsg('emergency-body', 'Could not fetch emergency data.');
    console.error(e);
  }
}

// ── 5. Map Visualisation ──────────────────────────────────────
function renderMap() {
  const container = el('traffic-map');
  const W = container.clientWidth || 600;
  const H = 340;

  // Build nodes from trafficData
  const roads = trafficData.slice(0, 12); // limit for clarity
  const n     = roads.length;
  if (!n) { container.innerHTML = '<div class="loader">No roads to display.</div>'; return; }

  // Place nodes in a circle or grid
  const cx = W / 2, cy = H / 2;
  const r  = Math.min(W, H) * 0.35;

  const positions = roads.map((_, i) => {
    const angle = (2 * Math.PI * i / n) - Math.PI / 2;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });

  // Draw using SVG
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('width', W);
  svg.setAttribute('height', H);
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.style.display = 'block';

  // Background
  const bg = document.createElementNS(ns, 'rect');
  bg.setAttribute('width', W); bg.setAttribute('height', H);
  bg.setAttribute('fill', '#f8faff'); bg.setAttribute('rx', '12');
  svg.appendChild(bg);

  // Edges (connections between consecutive nodes)
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    const line = document.createElementNS(ns, 'line');
    line.setAttribute('x1', positions[i].x); line.setAttribute('y1', positions[i].y);
    line.setAttribute('x2', positions[j].x); line.setAttribute('y2', positions[j].y);
    line.setAttribute('stroke', '#cbd5e1');
    line.setAttribute('stroke-width', '1.5');
    line.setAttribute('stroke-dasharray', '4 3');
    svg.appendChild(line);
  }

  // Nodes
  roads.forEach((road, i) => {
    const vehicles = Number(road.vehicle_count ?? road.vehicles ?? 0);
    const capacity = Number(road.capacity ?? 100);
    const pct      = capacity > 0 ? vehicles / capacity : 0;
    const status   = (road.congestion_status ?? road.status ?? '').toString().toLowerCase();
    const isCong   = status.includes('congest');
    const fill     = isCong ? '#ef4444' : pct > 0.5 ? '#f59e0b' : '#22c55e';
    const nodeR    = 18 + Math.min(pct * 12, 12);
    const pos      = positions[i];
    const name     = road.road ?? road.name ?? `R${i+1}`;

    // Glow
    const glow = document.createElementNS(ns, 'circle');
    glow.setAttribute('cx', pos.x); glow.setAttribute('cy', pos.y);
    glow.setAttribute('r', nodeR + 6);
    glow.setAttribute('fill', fill + '22');
    svg.appendChild(glow);

    // Circle
    const circle = document.createElementNS(ns, 'circle');
    circle.setAttribute('cx', pos.x); circle.setAttribute('cy', pos.y);
    circle.setAttribute('r', nodeR);
    circle.setAttribute('fill', fill);
    circle.setAttribute('stroke', '#fff');
    circle.setAttribute('stroke-width', '2');
    svg.appendChild(circle);

    // Count label
    const countTxt = document.createElementNS(ns, 'text');
    countTxt.setAttribute('x', pos.x); countTxt.setAttribute('y', pos.y + 1);
    countTxt.setAttribute('text-anchor', 'middle');
    countTxt.setAttribute('dominant-baseline', 'middle');
    countTxt.setAttribute('fill', '#fff');
    countTxt.setAttribute('font-size', '9');
    countTxt.setAttribute('font-weight', '700');
    countTxt.setAttribute('font-family', 'Inter, sans-serif');
    countTxt.textContent = vehicles > 999 ? `${(vehicles/1000).toFixed(1)}k` : vehicles;
    svg.appendChild(countTxt);

    // Road label
    const label = document.createElementNS(ns, 'text');
    const labelY = pos.y > cy ? pos.y + nodeR + 14 : pos.y - nodeR - 6;
    label.setAttribute('x', pos.x); label.setAttribute('y', labelY);
    label.setAttribute('text-anchor', 'middle');
    label.setAttribute('fill', '#475569');
    label.setAttribute('font-size', '10');
    label.setAttribute('font-weight', '600');
    label.setAttribute('font-family', 'Inter, sans-serif');
    label.textContent = name.length > 12 ? name.slice(0, 10) + '…' : name;
    svg.appendChild(label);
  });

  // Legend
  const legendData = [
    { color: '#22c55e', label: 'Normal' },
    { color: '#f59e0b', label: 'Moderate' },
    { color: '#ef4444', label: 'Congested' },
  ];
  legendData.forEach((item, i) => {
    const lx = 16, ly = H - 16 - i * 18;
    const dot = document.createElementNS(ns, 'circle');
    dot.setAttribute('cx', lx); dot.setAttribute('cy', ly - 4); dot.setAttribute('r', 5);
    dot.setAttribute('fill', item.color); svg.appendChild(dot);
    const ltxt = document.createElementNS(ns, 'text');
    ltxt.setAttribute('x', lx + 10); ltxt.setAttribute('y', ly);
    ltxt.setAttribute('fill', '#475569'); ltxt.setAttribute('font-size', '10');
    ltxt.setAttribute('font-family', 'Inter, sans-serif');
    ltxt.textContent = item.label; svg.appendChild(ltxt);
  });

  container.innerHTML = '';
  container.appendChild(svg);
}

// ── 6. Chart ──────────────────────────────────────────────────
function renderChart() {
  const canvas = el('traffic-chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const labels  = trafficData.map(r => r.road ?? r.name ?? '?');
  const counts  = trafficData.map(r => Number(r.vehicle_count ?? r.vehicles ?? 0));
  const colors  = trafficData.map(r => {
    const s = (r.congestion_status ?? r.status ?? '').toString().toLowerCase();
    return s.includes('congest') ? 'rgba(239,68,68,0.75)' : 'rgba(59,130,246,0.75)';
  });

  if (chartInstance) { chartInstance.destroy(); chartInstance = null; }

  chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Vehicle Count',
        data:  counts,
        backgroundColor: colors,
        borderColor:     colors.map(c => c.replace('0.75', '1')),
        borderWidth: 1.5,
        borderRadius: 5,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: ctx => ` ${fmt(ctx.parsed.y)} vehicles` },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { family: 'Inter', size: 11 }, color: '#64748b' },
        },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: { font: { family: 'Inter', size: 11 }, color: '#64748b' },
          beginAtZero: true,
        },
      },
    },
  });
}

// ── 6. AI Traffic Predictions ────────────────────────────────
async function loadPredictions() {
  const body = el('prediction-body');
  if (!body) return;
  if (!trafficData.length) { body.innerHTML = '<div class="loader"><div class="spinner"></div>Waiting for traffic data…</div>'; return; }

  body.innerHTML = '<div class="loader"><div class="spinner"></div>Computing predictions…</div>';

  try {
    const results = await Promise.all(
      trafficData.map(r => fetchJSON(API.predict(r.road ?? r.name)).catch(() => null))
    );

    // Update KPI total predicted
    const totalPred = results.reduce((s, r) => s + (r ? r.predicted : 0), 0);
    const kpiPred = el('kpi-predicted');
    if (kpiPred) kpiPred.textContent = fmt(totalPred);

    body.innerHTML = results.map(r => {
      if (!r) return '';
      const delta = r.predicted - r.current;
      const arrow = delta > 0 ? '▲' : delta < 0 ? '▼' : '→';
      const color = delta > 0 ? '#ef4444' : delta < 0 ? '#22c55e' : '#64748b';
      return `
        <div class="schedule-item">
          <div>
            <div class="schedule-batch">${r.road}</div>
            <div class="schedule-info">Now: ${fmt(r.current)} vehicles</div>
          </div>
          <span class="schedule-count" style="color:${color}">
            ${arrow} ${fmt(r.predicted)}
          </span>
        </div>`;
    }).join('');
  } catch (e) {
    body.innerHTML = '<div class="error-msg">⚠ Could not load predictions.</div>';
    console.error(e);
  }
}

// ── Refresh All ───────────────────────────────────────────────
async function refreshAll() {
  el('refresh-btn').disabled = true;
  await Promise.all([loadTraffic(), loadSchedule(), loadEmergency()]);
  await loadPredictions(); // after traffic data is loaded
  el('refresh-btn').disabled = false;
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  refreshAll();

  el('refresh-btn').addEventListener('click', refreshAll);
  el('get-route-btn').addEventListener('click', loadRoute);

  // Auto-refresh every 5 s (real-time simulation)
  setInterval(refreshAll, 5_000);
});
