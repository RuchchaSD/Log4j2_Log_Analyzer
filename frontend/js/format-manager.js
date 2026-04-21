// Format Type Manager — CRUD UI for log4j2 layout pattern types
const FormatManager = {

  _formats: [],   // cached list (built-ins + user-defined)

  // ── Load and cache all formats ─────────────────────────────────────────────
  async loadFormats() {
    try {
      const { formats } = await api.listFormats();
      FormatManager._formats = formats || [];
      return FormatManager._formats;
    } catch (err) {
      Toast.error('Failed to load format types');
      return [];
    }
  },

  // ── Return cached list (load if empty) ────────────────────────────────────
  async getFormats() {
    if (FormatManager._formats.length === 0) await FormatManager.loadFormats();
    return FormatManager._formats;
  },

  // ── Render the format list in the Settings tab ────────────────────────────
  async renderFormatList() {
    const container = document.getElementById('format-list');
    if (!container) return;

    container.innerHTML = '<div class="loading-row"><div class="spinner"></div> Loading…</div>';
    const formats = await FormatManager.loadFormats();

    if (formats.length === 0) {
      container.innerHTML = '<div style="padding:16px;font-size:12px;color:var(--text-muted)">No format types found.</div>';
      return;
    }

    container.innerHTML = '';
    formats.forEach(fmt => container.appendChild(_formatRow(fmt)));
  },

  // ── Show create/edit modal ─────────────────────────────────────────────────
  showCreateModal() {
    _showFormatModal(null);
  },

  showEditModal(formatId) {
    const fmt = FormatManager._formats.find(f => f.id === formatId);
    if (!fmt) return;
    if (fmt.is_builtin) { Toast.warn('Built-in formats cannot be edited'); return; }
    _showFormatModal(fmt);
  },

  // ── Delete ─────────────────────────────────────────────────────────────────
  async deleteFormat(formatId, name) {
    if (!window.confirm(`Delete format type "${name}"?`)) return;
    try {
      await api.deleteFormat(formatId);
      Toast.success(`Deleted "${name}"`);
      FormatManager._formats = [];          // invalidate cache
      FormatManager.renderFormatList();
    } catch (err) {
      Toast.error(`Failed to delete: ${err.message}`);
    }
  },

  // ── Build a <select> element populated with all formats ───────────────────
  async buildSelect(selectedId, includeNone = true) {
    const formats = await FormatManager.getFormats();
    const sel = document.createElement('select');
    sel.className = 'form-select';

    if (includeNone) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = '— Auto-detect —';
      sel.appendChild(opt);
    }

    formats.forEach(fmt => {
      const opt = document.createElement('option');
      opt.value = fmt.id;
      opt.textContent = fmt.name + (fmt.is_builtin ? ' (built-in)' : '');
      if (fmt.id === selectedId) opt.selected = true;
      sel.appendChild(opt);
    });

    return sel;
  },
};

// ── Private helpers ────────────────────────────────────────────────────────────

function _formatRow(fmt) {
  const row = document.createElement('div');
  row.className = 'format-row';
  row.dataset.formatId = fmt.id;

  const builtinBadge = fmt.is_builtin
    ? '<span class="badge badge-info" style="font-size:10px">built-in</span>'
    : '';
  const productBadge = fmt.product
    ? `<span class="badge badge-generic" style="font-size:10px">${_esc(fmt.product)}</span>`
    : '';

  row.innerHTML = `
    <div class="format-row-header">
      <span class="format-row-name">${_esc(fmt.name)}</span>
      <span class="format-row-badges">${builtinBadge}${productBadge}</span>
    </div>
    <code class="format-row-pattern">${_esc(fmt.pattern)}</code>
    ${fmt.description ? `<div class="format-row-desc">${_esc(fmt.description)}</div>` : ''}
    <div class="format-row-actions">
      ${!fmt.is_builtin ? `
        <button class="btn btn-ghost btn-xs" onclick="FormatManager.showEditModal('${fmt.id}')">Edit</button>
        <button class="btn btn-ghost btn-xs btn-danger-text" onclick="FormatManager.deleteFormat('${fmt.id}', '${_esc(fmt.name)}')">Delete</button>
      ` : ''}
      <button class="btn btn-ghost btn-xs" onclick="FormatManager._showTestModal('${fmt.id}')">Test</button>
    </div>`;

  return row;
}

function _showFormatModal(existing) {
  const isEdit = !!existing;
  const body = `
    <div class="form-group">
      <label class="form-label">Name <span class="required">*</span></label>
      <input id="fmt-name" class="form-input" type="text"
             placeholder="MI_4.3.0_Carbon" value="${existing ? _esc(existing.name) : ''}" autofocus />
    </div>
    <div class="form-group">
      <label class="form-label">log4j2 Pattern <span class="required">*</span></label>
      <input id="fmt-pattern" class="form-input" type="text"
             placeholder="[%d] %5p {%c} - %m%ex%n"
             value="${existing ? _esc(existing.pattern) : ''}" />
      <span class="form-hint">Use standard log4j2 directives: %d, %p, %c, %t, %m, %ex, %n, [%tenantId], [%appName]</span>
    </div>
    <div class="form-group">
      <label class="form-label">Description</label>
      <input id="fmt-desc" class="form-input" type="text"
             placeholder="Optional description"
             value="${existing ? _esc(existing.description) : ''}" />
    </div>
    <div class="form-group">
      <label class="form-label">Product</label>
      <select id="fmt-product" class="form-select">
        <option value="">— none —</option>
        ${['apim','is','mi','ei','generic'].map(p =>
          `<option value="${p}"${existing?.product === p ? ' selected' : ''}>${p.toUpperCase()}</option>`
        ).join('')}
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">Test pattern (optional)</label>
      <input id="fmt-test-line" class="form-input" type="text"
             placeholder="Paste a sample log line to verify…" />
      <button type="button" class="btn btn-ghost btn-sm" style="margin-top:6px"
              onclick="FormatManager._inlineTest()">Test Pattern</button>
      <div id="fmt-test-result" style="margin-top:6px;font-size:12px"></div>
    </div>`;

  const footer = `
    <button class="btn btn-ghost" onclick="Modal.hide()">Cancel</button>
    <button class="btn btn-primary" onclick="FormatManager._saveFormat('${isEdit ? existing.id : ''}')">
      ${isEdit ? 'Save Changes' : 'Create Format Type'}
    </button>`;

  Modal.show(isEdit ? 'Edit Format Type' : 'New Format Type', body, footer);
}

FormatManager._inlineTest = async function () {
  const pattern = document.getElementById('fmt-pattern')?.value.trim();
  const line = document.getElementById('fmt-test-line')?.value.trim();
  const resultEl = document.getElementById('fmt-test-result');
  if (!pattern || !line) { resultEl.textContent = 'Enter both pattern and a sample line.'; return; }

  try {
    const result = await api.testFormatPattern(pattern, line);
    if (result.error) {
      resultEl.innerHTML = `<span style="color:var(--accent-red)">Error: ${_esc(result.error)}</span>`;
    } else if (!result.matched) {
      resultEl.innerHTML = `<span style="color:var(--accent-amber)">No match. Check the pattern against this line.</span>`;
    } else {
      const fields = Object.entries(result.fields)
        .map(([k, v]) => `<span><b>${_esc(k)}:</b> ${_esc(v)}</span>`)
        .join(' · ');
      resultEl.innerHTML = `<span style="color:var(--accent-green)">✓ Matched:</span> ${fields}`;
    }
  } catch (err) {
    resultEl.innerHTML = `<span style="color:var(--accent-red)">Request failed: ${_esc(err.message)}</span>`;
  }
};

FormatManager._saveFormat = async function (existingId) {
  const name = document.getElementById('fmt-name')?.value.trim();
  const pattern = document.getElementById('fmt-pattern')?.value.trim();
  const description = document.getElementById('fmt-desc')?.value.trim();
  const product = document.getElementById('fmt-product')?.value || null;

  if (!name) { Toast.error('Name is required'); return; }
  if (!pattern) { Toast.error('Pattern is required'); return; }

  const btn = document.querySelector('#modal-footer .btn-primary');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner spinner-sm"></div> Saving…';

  try {
    if (existingId) {
      await api.updateFormat(existingId, { name, pattern, description, product });
      Toast.success(`Updated "${name}"`);
    } else {
      await api.createFormat({ name, pattern, description, product });
      Toast.success(`Created "${name}"`);
    }
    FormatManager._formats = [];      // invalidate cache
    Modal.hide();
    FormatManager.renderFormatList();
  } catch (err) {
    Toast.error(`Failed to save: ${err.message}`);
    btn.disabled = false;
    btn.innerHTML = existingId ? 'Save Changes' : 'Create Format Type';
  }
};

FormatManager._showTestModal = function (formatId) {
  const fmt = FormatManager._formats.find(f => f.id === formatId);
  if (!fmt) return;

  const body = `
    <div class="form-group">
      <label class="form-label">Pattern</label>
      <code style="display:block;padding:8px;background:var(--bg-tertiary);border-radius:4px;font-size:12px;word-break:break-all">${_esc(fmt.pattern)}</code>
    </div>
    <div class="form-group">
      <label class="form-label">Sample log line</label>
      <input id="test-sample-line" class="form-input" type="text"
             placeholder="Paste a line from your log file…" autofocus />
    </div>
    <div id="test-result" style="margin-top:8px;font-size:12px"></div>`;

  const footer = `
    <button class="btn btn-ghost" onclick="Modal.hide()">Close</button>
    <button class="btn btn-primary" onclick="FormatManager._runTest('${_esc(fmt.pattern)}')">Test</button>`;

  Modal.show(`Test: ${fmt.name}`, body, footer);
};

FormatManager._runTest = async function (pattern) {
  const line = document.getElementById('test-sample-line')?.value.trim();
  const resultEl = document.getElementById('test-result');
  if (!line) { resultEl.textContent = 'Paste a log line first.'; return; }

  try {
    const result = await api.testFormatPattern(pattern, line);
    if (result.error) {
      resultEl.innerHTML = `<span style="color:var(--accent-red)">Error: ${_esc(result.error)}</span>`;
    } else if (!result.matched) {
      resultEl.innerHTML = `<span style="color:var(--accent-amber)">No match.</span>`;
    } else {
      const rows = Object.entries(result.fields)
        .map(([k, v]) => `<tr><td style="padding:2px 8px 2px 0;font-weight:600">${_esc(k)}</td><td>${_esc(v)}</td></tr>`)
        .join('');
      resultEl.innerHTML = `<span style="color:var(--accent-green)">✓ Matched</span><table style="margin-top:6px;font-size:12px">${rows}</table>`;
    }
  } catch (err) {
    resultEl.innerHTML = `<span style="color:var(--accent-red)">${_esc(err.message)}</span>`;
  }
};

function _esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
