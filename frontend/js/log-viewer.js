// ── Log Viewer ────────────────────────────────────────────────────────────────
const LogViewer = (() => {
  const ITEM_HEIGHT = 24;       // px per row (estimate)
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

  // ── Public API ──────────────────────────────────────────────────────────────

  async function loadFile(logFileId, projectId) {
    _logFileId = logFileId;
    _projectId = projectId;
    _entries = [];
    _total = 0;
    _offset = 0;
    _selectedIndex = null;
    _expandedIndices.clear();
    closeDetail();
    _renderEntries();
    _showLoading(true);
    await _fetchAndAppend(0);
    _showLoading(false);
    _updateStats();
  }

  async function applyFilters() {
    if (!_logFileId) return;
    _entries = [];
    _total = 0;
    _offset = 0;
    _selectedIndex = null;
    _expandedIndices.clear();
    closeDetail();
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
    try {
      const levels = _activeLevels.size < 6 ? [..._activeLevels] : null;
      const hasStackTrace = _activeFilters.stackOnly ? true : null;

      let data;
      if (_activeFilters.search || levels || hasStackTrace || _activeFilters.errorsOnly) {
        // Use filter endpoint
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

      _entries = [..._entries, ...data.entries];
      _total = data.total;
      _offset = offset + data.entries.length;
      _renderEntries();
    } catch(e) {
      Toast.error('Failed to load log entries: ' + e.message);
    } finally {
      _loading = false;
    }
  }

  // ── Virtual Scroll Rendering ─────────────────────────────────────────────────

  function _renderEntries() {
    const viewport = document.getElementById('log-viewport');
    const container = document.getElementById('log-entries-container');
    const spacerTop = document.getElementById('log-spacer-top');
    const spacerBottom = document.getElementById('log-spacer-bottom');
    if (!viewport || !container) return;

    const scrollTop = viewport.scrollTop;
    const viewportH = viewport.clientHeight;

    const startIdx = Math.max(0, Math.floor(scrollTop / ITEM_HEIGHT) - BUFFER);
    const endIdx = Math.min(_entries.length, Math.ceil((scrollTop + viewportH) / ITEM_HEIGHT) + BUFFER);

    spacerTop.style.height = (startIdx * ITEM_HEIGHT) + 'px';
    spacerBottom.style.height = ((_entries.length - endIdx) * ITEM_HEIGHT) + 'px';

    const fragment = document.createDocumentFragment();
    for (let i = startIdx; i < endIdx; i++) {
      fragment.appendChild(_buildRow(_entries[i], i));
    }
    container.innerHTML = '';
    container.appendChild(fragment);

    // Load more if near bottom
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
    const container = document.getElementById('log-entries-container');
    if (!container) return;
    if (show && _entries.length === 0) {
      container.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted)">Parsing log file...</div>';
    }
  }

  function _escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ── Init ─────────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', () => initFilterBar());

  return { loadFile, applyFilters, closeDetail, filterByCorrelation };
})();
