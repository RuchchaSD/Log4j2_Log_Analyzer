// ── Log Viewer ────────────────────────────────────────────────────────────────
const LogViewer = (() => {
  const ROW_H = 26;             // px per row — must match CSS .log-entry height
  const BUFFER = 40;            // extra rows rendered above/below viewport
  const PAGE_SIZE = 300;        // entries fetched per API call

  let _logFileId = null;
  let _projectId = null;
  let _entries = [];            // all currently loaded/filtered entries
  let _total = 0;
  let _offset = 0;
  let _loading = false;
  let _selectedIndex = null;
  let _expandedIndices = new Set();
  let _activeFilters = {
    levels: null,               // null = all
    search: '',
    regex: false,
    errorsOnly: false,
    stackOnly: false,
  };
  let _scrollRAF = null;
  let _searchDebounce = null;
  let _activeLevels = new Set(['FATAL','ERROR','WARN','INFO','DEBUG','TRACE']);
  let _generation = 0;   // incremented on reset/load — stale fetches discard their results

  // ── Public API ──────────────────────────────────────────────────────────────

  function _clearInner() {
    const inner = document.getElementById('log-scroll-inner');
    if (inner) { inner.innerHTML = ''; inner.style.height = '0px'; }
    // Reset scroll position
    const vp = document.getElementById('log-viewport');
    if (vp) vp.scrollTop = 0;
  }

  async function loadFile(logFileId, projectId) {
    _generation++;
    _loading = false;
    _logFileId = logFileId;
    _projectId = projectId;
    _entries = [];
    _total = 0;
    _offset = 0;
    _selectedIndex = null;
    _expandedIndices.clear();
    closeDetail();
    _clearInner();
    _showLoading(true);
    await _fetchAndAppend(0);
    _showLoading(false);
    _updateStats();
  }

  async function applyFilters() {
    if (!_logFileId) return;
    _generation++;
    _loading = false;
    _entries = [];
    _total = 0;
    _offset = 0;
    _selectedIndex = null;
    _expandedIndices.clear();
    closeDetail();
    _clearInner();
    _showLoading(true);
    await _fetchAndAppend(0);
    _showLoading(false);
    _updateStats();
  }

  function closeDetail() {
    document.getElementById('log-detail-panel').classList.add('hidden');
    _selectedIndex = null;
    document.querySelectorAll('.log-entry.selected').forEach(el => el.classList.remove('selected'));
  }

  // ── Fetch ───────────────────────────────────────────────────────────────────

  async function _fetchAndAppend(offset) {
    if (_loading) return;
    _loading = true;
    const gen = _generation;   // capture generation at fetch start
    try {
      const levels = _activeLevels.size < 6 ? [..._activeLevels] : null;
      const hasStackTrace = _activeFilters.stackOnly ? true : null;

      let data;
      if (_activeFilters.search || levels || hasStackTrace || _activeFilters.errorsOnly) {
        const filterLevels = _activeFilters.errorsOnly ? ['ERROR','FATAL'] : levels;
        const body = {
          levels: filterLevels || null,
          search: _activeFilters.search || null,
          regex: _activeFilters.regex,
          has_stack_trace: hasStackTrace,
          offset,
          limit: PAGE_SIZE,
        };
        data = await api.filterLog(_projectId, _logFileId, body);
      } else {
        data = await api.getLogEntries(_projectId, _logFileId, offset, PAGE_SIZE);
      }

      // Discard results if a reset/load happened while this fetch was in flight
      if (gen !== _generation) return;

      _entries = [..._entries, ...data.entries];
      _total = data.total;
      _offset = offset + data.entries.length;
      _renderEntries();
    } catch(e) {
      if (gen === _generation) Toast.error('Failed to load log entries: ' + e.message);
    } finally {
      _loading = false;
    }
  }

  // ── Virtual Scroll Rendering ─────────────────────────────────────────────────
  // Approach: #log-scroll-inner has position:relative and fixed height = N * ROW_H.
  // Each row is position:absolute with top = idx * ROW_H.
  // This means the scrollable height never changes during rendering, so the
  // browser's scroll momentum, scrollbar drag, and position are all stable.

  function _renderEntries() {
    const viewport = document.getElementById('log-viewport');
    const inner = document.getElementById('log-scroll-inner');
    if (!viewport || !inner) return;

    const totalH = _entries.length * ROW_H;

    // Only update height if it changed — avoid unnecessary style writes
    if (inner.style.height !== totalH + 'px') {
      inner.style.height = totalH + 'px';
    }

    const scrollTop = viewport.scrollTop;
    const viewportH = viewport.clientHeight || viewport.offsetHeight;

    const startIdx = Math.max(0, Math.floor(scrollTop / ROW_H) - BUFFER);
    const endIdx = Math.min(_entries.length, Math.ceil((scrollTop + viewportH) / ROW_H) + BUFFER);

    // Build a map of currently rendered rows by index for diffing
    const existing = new Map();
    for (const child of inner.children) {
      existing.set(+child.dataset.idx, child);
    }

    // Remove rows that are now out of the window
    for (const [idx, el] of existing) {
      if (idx < startIdx || idx >= endIdx) {
        inner.removeChild(el);
        existing.delete(idx);
      }
    }

    // Add rows that are now in the window but not rendered
    const fragment = document.createDocumentFragment();
    for (let i = startIdx; i < endIdx; i++) {
      if (!existing.has(i)) {
        const row = _buildRow(_entries[i], i);
        row.style.top = (i * ROW_H) + 'px';
        fragment.appendChild(row);
      }
    }
    if (fragment.childNodes.length > 0) {
      inner.appendChild(fragment);
    }

    // Fetch more entries if near the loaded bottom
    if (_entries.length < _total && endIdx >= _entries.length - 20) {
      _fetchAndAppend(_offset);
    }
  }

  function _buildRow(entry, idx) {
    const row = document.createElement('div');
    const lvl = (entry.level || 'INFO').toLowerCase();
    row.className = `log-entry level-${lvl}`;
    if (idx === _selectedIndex) row.classList.add('selected');
    row.dataset.idx = idx;

    const ts = entry.timestamp ? entry.timestamp.split(' ')[1] || entry.timestamp : '';
    const msg = _escapeHtml(entry.message || '');
    const hasStack = entry.has_stack_trace;

    row.innerHTML = `
      <div class="log-col-linenum">${entry.line_number}</div>
      <div class="log-col-level level-${lvl}">${entry.level || ''}</div>
      <div class="log-col-time" title="${entry.timestamp || ''}">${ts}</div>
      <div class="log-col-logger" title="${entry.logger || ''}">${entry.logger_short || entry.logger || ''}</div>
      <div class="log-col-message${hasStack ? ' has-stack' : ''}">
        ${hasStack ? '<span class="stack-indicator">stack</span>' : ''}
        ${msg}
      </div>
    `;

    row.addEventListener('click', (e) => _onRowClick(entry, idx, row, e));
    return row;
  }

  function _onRowClick(entry, idx, row, e) {
    // Toggle selection
    if (_selectedIndex === idx) {
      closeDetail();
    } else {
      _selectedIndex = idx;
      document.querySelectorAll('.log-entry.selected').forEach(el => el.classList.remove('selected'));
      row.classList.add('selected');
      _showDetail(entry);
    }

    // Toggle stack trace inline expansion
    if (entry.has_stack_trace) {
      if (_expandedIndices.has(idx)) {
        _expandedIndices.delete(idx);
      } else {
        _expandedIndices.add(idx);
      }
      // Re-render to show/hide stack
      _renderEntries();
    }
  }

  // ── Detail Panel ────────────────────────────────────────────────────────────

  function _showDetail(entry) {
    const panel = document.getElementById('log-detail-panel');
    panel.classList.remove('hidden');

    const meta = [
      entry.timestamp ? `<span>${entry.timestamp}</span>` : '',
      `<span class="badge badge-${(entry.level||'').toLowerCase()}">${entry.level}</span>`,
      entry.logger ? `<span title="${_escapeHtml(entry.logger)}">${_escapeHtml(entry.logger_short || entry.logger)}</span>` : '',
      entry.tid ? `<span>TID: ${_escapeHtml(entry.tid)}</span>` : '',
      entry.app_name ? `<span>App: ${_escapeHtml(entry.app_name)}</span>` : '',
      entry.correlation_id ? `<span>CorrelationID: <a href="#" onclick="LogViewer.filterByCorrelation('${_escapeHtml(entry.correlation_id)}')">${_escapeHtml(entry.correlation_id)}</a></span>` : '',
    ].filter(Boolean).join('');

    document.getElementById('log-detail-meta').innerHTML = meta;
    document.getElementById('log-detail-message').textContent = entry.message || '';
    const stackEl = document.getElementById('log-detail-stack');
    if (entry.stack_trace && entry.stack_trace.length) {
      stackEl.textContent = entry.stack_trace.join('\n');
      stackEl.style.display = '';
    } else {
      stackEl.textContent = '';
      stackEl.style.display = 'none';
    }
  }

  async function filterByCorrelation(correlationId) {
    // Set a correlation filter and reload
    Toast.info(`Filtering by correlation ID: ${correlationId}`);
    // This would need UI support — for now just show a toast
  }

  // ── Filter bar wiring ────────────────────────────────────────────────────────

  function initFilterBar() {
    // Level toggles
    document.querySelectorAll('.level-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        const lvl = btn.dataset.level;
        btn.classList.toggle('active');
        if (_activeLevels.has(lvl)) _activeLevels.delete(lvl);
        else _activeLevels.add(lvl);
        applyFilters();
      });
    });

    // Search input with debounce
    const searchInput = document.getElementById('filter-search');
    if (searchInput) {
      searchInput.addEventListener('input', () => {
        clearTimeout(_searchDebounce);
        _searchDebounce = setTimeout(() => {
          const val = searchInput.value.trim();
          if (val.startsWith('/') && val.length > 2 && val.lastIndexOf('/') > 0) {
            // Regex mode: /pattern/
            const lastSlash = val.lastIndexOf('/');
            _activeFilters.search = val.slice(1, lastSlash);
            _activeFilters.regex = true;
          } else {
            _activeFilters.search = val;
            _activeFilters.regex = false;
          }
          applyFilters();
        }, 400);
      });
    }

    // Errors only checkbox
    const errCb = document.getElementById('filter-errors-only');
    if (errCb) errCb.addEventListener('change', () => { _activeFilters.errorsOnly = errCb.checked; applyFilters(); });

    // Stack trace only checkbox
    const stackCb = document.getElementById('filter-stack-only');
    if (stackCb) stackCb.addEventListener('change', () => { _activeFilters.stackOnly = stackCb.checked; applyFilters(); });

    // Virtual scroll on scroll event
    const viewport = document.getElementById('log-viewport');
    if (viewport) {
      viewport.addEventListener('scroll', () => {
        cancelAnimationFrame(_scrollRAF);
        _scrollRAF = requestAnimationFrame(_renderEntries);
      });
    }
  }

  function _updateStats() {
    const el = document.getElementById('filter-stats');
    if (el) {
      el.textContent = _total > 0 ? `${_entries.length.toLocaleString()} / ${_total.toLocaleString()} entries` : 'No entries';
    }
  }

  function _showLoading(show) {
    const el = document.getElementById('log-loading');
    const vp = document.getElementById('log-viewport');
    if (!el) return;
    el.classList.toggle('hidden', !show);
    if (vp) vp.classList.toggle('hidden', show);
  }

  function _escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ── Init ─────────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', () => initFilterBar());

  function reset() {
    _generation++;            // invalidate any in-flight fetches
    _loading = false;         // unblock future fetches
    _logFileId = null;
    _projectId = null;
    _entries = [];
    _total = 0;
    _offset = 0;
    _selectedIndex = null;
    _expandedIndices.clear();
    _activeLevels = new Set(['FATAL','ERROR','WARN','INFO','DEBUG','TRACE']);
    _activeFilters = { levels: null, search: '', regex: false, errorsOnly: false, stackOnly: false };
    closeDetail();
    _clearInner();
    _showLoading(false);
    _updateStats();
    // Reset filter bar UI
    document.querySelectorAll('.level-toggle').forEach(btn => btn.classList.add('active'));
    const s = document.getElementById('filter-search'); if (s) s.value = '';
    const e = document.getElementById('filter-errors-only'); if (e) e.checked = false;
    const t = document.getElementById('filter-stack-only'); if (t) t.checked = false;
  }

  return { loadFile, applyFilters, closeDetail, filterByCorrelation, reset };
})();
