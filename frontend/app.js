/* ═══════════════════════════════════════════════════════════════════
   app.js  —  ETL Studio frontend logic
   All API calls, table rendering, sorting, and UI state management.
   ═══════════════════════════════════════════════════════════════════ */

const API = '/api/v1/etl';

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  projectId: null,
  instructions: [],
  excelTables: [],
  matchResults: [],
  sortCol: null,
  sortDir: 'asc',
};

// ── DOM refs ──────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const pptInput       = $('pptInput');
const excelInput     = $('excelInput');
const btnUploadPPT   = $('btnUploadPPT');
const btnUploadExcel = $('btnUploadExcel');
const btnProceed     = $('btnProceed');
const btnSort        = $('btnSort');
const btnMap         = $('btnMap');
const btnDLPPT       = $('btnDownloadPPT');
const btnDLXLS       = $('btnDownloadXLS');
const projectBadge   = $('projectBadge');
const loaderOverlay  = $('loaderOverlay');
const loaderText     = $('loaderText');

// ── Utility: toast notifications ─────────────────────────────────────────
function toast(msg, type = 'info', duration = 4000) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
  $('toastContainer').prepend(el);
  setTimeout(() => el.remove(), duration);
}

// ── Utility: loader ───────────────────────────────────────────────────────
function showLoader(text = 'Processing…') {
  loaderText.textContent = text;
  loaderOverlay.style.display = 'flex';
}
function hideLoader() {
  loaderOverlay.style.display = 'none';
}

// ── Utility: step state ───────────────────────────────────────────────────
function setStep(n, state_) {
  const card = $(`card${n}`);
  const status = $(`status${n}`);
  card.classList.remove('active', 'done');
  if (state_ === 'active') { card.classList.add('active'); status.textContent = '🔵'; }
  if (state_ === 'done')   { card.classList.add('done');   status.textContent = '✅'; }
  if (state_ === 'idle')   { status.textContent = '⬜'; }
}

// ── Utility: API fetch ────────────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || 'API error');
  }
  return resp.json();
}

// ═══════════════════════════════════════════════════════════════════════════
// INIT PROJECT
// ═══════════════════════════════════════════════════════════════════════════
async function initProject() {
  const data = await apiFetch(`${API}/projects`, { method: 'POST' });
  state.projectId = data.project_id;
  projectBadge.textContent = `ID: ${data.project_id.slice(0, 8)}…`;
  setStep(1, 'active');
}

// ═══════════════════════════════════════════════════════════════════════════
// STEP 1 — Upload PPT
// ═══════════════════════════════════════════════════════════════════════════
pptInput.addEventListener('change', () => {
  if (pptInput.files[0]) {
    $('pptName').textContent = pptInput.files[0].name;
    btnUploadPPT.disabled = false;
  }
});

btnUploadPPT.addEventListener('click', async () => {
  if (!state.projectId) await initProject();
  const file = pptInput.files[0];
  if (!file) return;

  showLoader('Parsing PPT — extracting all shapes, boxes, and symbols…');
  try {
    const fd = new FormData();
    fd.append('file', file);
    const data = await apiFetch(
      `${API}/projects/${state.projectId}/upload-ppt`,
      { method: 'POST', body: fd }
    );
    state.instructions = data.instructions;
    renderInstructionTable(state.instructions);
    setStep(1, 'done');
    setStep(2, 'active');
    btnUploadExcel.disabled = false;
    btnSort.disabled = false;
    toast(`✔ Extracted ${data.total} unique instructions from PPT`, 'success');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    hideLoader();
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// STEP 2 — Upload Excel
// ═══════════════════════════════════════════════════════════════════════════
excelInput.addEventListener('change', () => {
  if (excelInput.files[0]) {
    $('excelName').textContent = excelInput.files[0].name;
    btnUploadExcel.disabled = false;
  }
});

btnUploadExcel.addEventListener('click', async () => {
  const file = excelInput.files[0];
  if (!file || !state.projectId) return;

  showLoader('Scanning Excel — detecting tables and normalising names…');
  try {
    const fd = new FormData();
    fd.append('file', file);
    const data = await apiFetch(
      `${API}/projects/${state.projectId}/upload-excel`,
      { method: 'POST', body: fd }
    );
    state.excelTables = data.table_details || [];
    renderExcelTable(state.excelTables);
    setStep(2, 'done');
    setStep(3, 'active');
    btnProceed.disabled = false;
    toast(`✔ Detected ${data.tables_detected} tables in Excel`, 'success');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    hideLoader();
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// STEP 3 — Extract & Match
// ═══════════════════════════════════════════════════════════════════════════
btnProceed.addEventListener('click', async () => {
  if (!state.projectId) return;
  showLoader('Matching PPT instructions to Excel tables…');
  try {
    const data = await apiFetch(
      `${API}/projects/${state.projectId}/extract-data`,
      { method: 'POST' }
    );
    state.matchResults = data.results;
    renderMatchTable(state.matchResults, data.matches_found, data.unmatched);
    setStep(3, 'done');
    btnMap.disabled = false;
    btnDLXLS.disabled = false;
    toast(`✔ ${data.matches_found} matched, ${data.unmatched} unmatched`, 'success');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    hideLoader();
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// MAP & PASTE
// ═══════════════════════════════════════════════════════════════════════════
btnMap.addEventListener('click', async () => {
  if (!state.projectId) return;
  showLoader('Rendering charts and pasting back into PPT…');
  try {
    const data = await apiFetch(
      `${API}/projects/${state.projectId}/map-and-paste`,
      { method: 'POST' }
    );
    renderResult(data);
    btnDLPPT.disabled = false;
    toast('✔ Charts pasted into PPT. Ready to download!', 'success');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    hideLoader();
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// DOWNLOADS
// ═══════════════════════════════════════════════════════════════════════════
btnDLPPT.addEventListener('click', () => {
  if (!state.projectId) return;
  window.location.href = `${API}/projects/${state.projectId}/download-final-ppt`;
});

btnDLXLS.addEventListener('click', () => {
  if (!state.projectId) return;
  window.location.href = `${API}/projects/${state.projectId}/download-extracted-excel`;
});

// ═══════════════════════════════════════════════════════════════════════════
// SORTING
// ═══════════════════════════════════════════════════════════════════════════
btnSort.addEventListener('click', () => {
  // Toggle sort on slide_number by default
  const col = 'slide_number';
  if (state.sortCol === col) {
    state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    state.sortCol = col;
    state.sortDir = 'asc';
  }
  const sorted = [...state.instructions].sort((a, b) => {
    const av = a[col], bv = b[col];
    if (av < bv) return state.sortDir === 'asc' ? -1 : 1;
    if (av > bv) return state.sortDir === 'asc' ? 1 : -1;
    return 0;
  });
  renderInstructionTable(sorted);
  toast(`Sorted by ${col} (${state.sortDir})`, 'info', 2000);
});

// Column-header click sorting
document.addEventListener('click', e => {
  const th = e.target.closest('th.sortable');
  if (!th || !th.dataset.col) return;
  const col = th.dataset.col;
  if (state.sortCol === col) {
    state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    state.sortCol = col;
    state.sortDir = 'asc';
  }
  const sorted = [...state.instructions].sort((a, b) => {
    const av = a[col], bv = b[col];
    if (av < bv) return state.sortDir === 'asc' ? -1 : 1;
    if (av > bv) return state.sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  // Update header arrows
  document.querySelectorAll('#instrTable th.sortable').forEach(t => {
    t.classList.remove('sort-asc', 'sort-desc');
    if (t.dataset.col === col) t.classList.add(`sort-${state.sortDir}`);
  });
  fillInstrBody(sorted);
});

// ═══════════════════════════════════════════════════════════════════════════
// RENDER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

function showPanel(id) {
  document.querySelectorAll('.panel').forEach(p => (p.style.display = 'none'));
  $('splash').style.display = 'none';
  $(id).style.display = 'block';
}

function renderInstructionTable(instrs) {
  $('instrCount').textContent = `${instrs.length} item${instrs.length !== 1 ? 's' : ''} found`;

  const types = instrs.reduce((acc, i) => { acc[i.type] = (acc[i.type] || 0) + 1; return acc; }, {});
  const statRow = $('statRow');
  statRow.innerHTML = Object.entries(types)
    .map(([k, v]) => `<div class="stat-chip">${badgeHtml(k)} ${v}</div>`)
    .join('');

  fillInstrBody(instrs);
  showPanel('panelInstructions');
}

function fillInstrBody(instrs) {
  const tbody = $('instrBody');
  tbody.innerHTML = instrs.map(i => `
    <tr>
      <td>${i.id}</td>
      <td>Slide ${i.slide_number}</td>
      <td title="${esc(i.shape_name)}">${esc(i.shape_name)}</td>
      <td>${badgeHtml(i.type)}</td>
      <td title="${esc(i.raw_text)}">${esc(i.raw_text)}</td>
    </tr>
  `).join('');
}

function renderExcelTable(tables) {
  const tbody = $('excelBody');
  tbody.innerHTML = tables.map(t => `
    <tr>
      <td>${esc(t.sheet_name)}</td>
      <td>${esc(t.table_name)}</td>
      <td><code style="color:var(--accent)">${esc(t.normalized_name)}</code></td>
      <td>${t.question_codes.slice(0, 6).join(', ') || '—'}</td>
      <td>${t.row_count}</td>
      <td>${t.col_count}</td>
    </tr>
  `).join('');
  // Show both panels
  $('panelInstructions').style.display = 'block';
  $('panelExcel').style.display = 'block';
  $('splash').style.display = 'none';
}

function renderMatchTable(results, matched, unmatched) {
  const tbody = $('matchBody');
  tbody.innerHTML = results.map(r => `
    <tr>
      <td>Slide ${r.slide_number}</td>
      <td title="${esc(r.raw_text)}">${esc(r.raw_text.substring(0, 60))}${r.raw_text.length > 60 ? '…' : ''}</td>
      <td>${badgeHtml(r.type)}</td>
      <td>${r.matched_table ? esc(r.matched_table) : '<span style="color:var(--text-muted)">—</span>'}</td>
      <td>${badgeHtml(r.match_confidence, 'confidence')}</td>
      <td>${r.match_score > 0 ? r.match_score.toFixed(0) + '%' : '—'}</td>
      <td>${r.matched_q_codes.join(', ') || '—'}</td>
    </tr>
  `).join('');

  $('matchStatRow').innerHTML = `
    <div class="stat-chip green">✔ ${matched} matched</div>
    <div class="stat-chip red">✘ ${unmatched} unmatched</div>
  `;

  $('panelInstructions').style.display = 'block';
  $('panelExcel').style.display = 'block';
  $('panelMatch').style.display = 'block';
  $('splash').style.display = 'none';
}

function renderResult(data) {
  $('resultGrid').innerHTML = `
    <div class="result-card">
      <div class="result-card-icon">📈</div>
      <div class="result-card-value">${data.charts_inserted}</div>
      <div class="result-card-label">Charts Inserted</div>
    </div>
    <div class="result-card">
      <div class="result-card-icon">⚡</div>
      <div class="result-card-value">${data.symbols_handled}</div>
      <div class="result-card-label">Symbols Handled</div>
    </div>
    <div class="result-card">
      <div class="result-card-icon">✅</div>
      <div class="result-card-value">Done</div>
      <div class="result-card-label">Status</div>
    </div>
    <div class="result-card">
      <div class="result-card-icon">⬇️</div>
      <div class="result-card-value" style="font-size:16px;margin-top:8px;">
        <button class="btn btn-map" onclick="document.getElementById('btnDownloadPPT').click()">Download Final PPT</button>
      </div>
      <div class="result-card-label">Get your file</div>
    </div>
  `;
  $('panelResult').style.display = 'block';
}

// ── Helpers ───────────────────────────────────────────────────────────────
function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function badgeHtml(type, mode = 'type') {
  const map = {
    instruction: 'badge-instruction',
    symbol:      'badge-symbol',
    unknown:     'badge-unknown',
    exact:       'badge-exact',
    fuzzy:       'badge-fuzzy',
    unmatched:   'badge-unmatched',
  };
  const cls = map[type] || 'badge-unknown';
  return `<span class="badge ${cls}">${esc(type)}</span>`;
}

// ── Kick off: create project on load ─────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  try {
    await initProject();
  } catch (e) {
    toast('Could not connect to API. Make sure the backend is running.', 'error', 8000);
  }
});
