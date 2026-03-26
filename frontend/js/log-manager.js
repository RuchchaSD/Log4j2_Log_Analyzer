// Log Manager UI
const LogManager = {

  // ── Render log files list (sidebar style) ─────────────────────────────────
  async renderLogFiles() {
    const projectId = App.state.currentProject?.id;
    if (!projectId) return;

    const container = document.getElementById('log-file-list-sidebar');
    if (!container) return;
    container.innerHTML = '<div class="loading-row"><div class="spinner"></div> Loading…</div>';

    try {
      const { logs } = await api.listLogs(projectId);

      if (!logs || logs.length === 0) {
        container.innerHTML = `
          <div class="log-viewer-empty" style="padding:24px;text-align:center;">
            <div style="font-size:28px">📄</div>
            <div style="font-size:12px;color:var(--text-muted)">No log files loaded</div>
            <div style="font-size:11px;color:var(--text-muted)">Use + or folder buttons above</div>
          </div>`;
        return;
      }

      container.innerHTML = '';
      logs.forEach(l => {
        container.appendChild(_logSidebarItem(l, projectId));
      });
    } catch (err) {
      container.innerHTML = `
        <div style="padding:16px;font-size:12px;color:var(--accent-red)">Failed: ${_esc(err.message)}</div>`;
    }
  },

  // ── Upload modal ───────────────────────────────────────────────────────────
  showUploadModal() {
    const body = `
      <div id="upload-dropzone" class="dropzone" onclick="document.getElementById('upload-file-input').click()">
        <input id="upload-file-input" type="file" accept=".log,.txt" multiple />
        <div class="dropzone-icon">📤</div>
        <div class="dropzone-title">Drop log files here, or click to browse</div>
        <div class="dropzone-subtitle">Supported: .log, .txt · Multiple files allowed</div>
        <div class="dropzone-hint" id="dropzone-hint">No files selected</div>
      </div>`;

    const footer = `
      <button class="btn btn-ghost" onclick="Modal.hide()">Cancel</button>
      <button class="btn btn-primary" id="upload-btn" onclick="LogManager._doUpload()" disabled>Upload</button>`;

    Modal.show('Upload Log Files', body, footer);

    // Wire up file input
    const fileInput = document.getElementById('upload-file-input');
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        LogManager._setSelectedFiles(Array.from(fileInput.files));
      }
    });

    // Wire up drag-and-drop
    const dz = document.getElementById('upload-dropzone');
    dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('drag-over'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
    dz.addEventListener('drop', (e) => {
      e.preventDefault();
      dz.classList.remove('drag-over');
      const files = Array.from(e.dataTransfer.files).filter(
        f => f.name.endsWith('.log') || f.name.endsWith('.txt')
      );
      if (files.length > 0) LogManager._setSelectedFiles(files);
    });
  },

  _setSelectedFiles(files) {
    LogManager._pendingFiles = files;
    const hint = document.getElementById('dropzone-hint');
    if (files.length === 1) {
      hint.innerHTML =
        `<span class="dropzone-filename">${_esc(files[0].name)}</span>
         <span style="color:var(--text-muted)"> · ${_formatSize(files[0].size)}</span>`;
    } else {
      const totalSize = files.reduce((sum, f) => sum + f.size, 0);
      hint.innerHTML =
        `<span class="dropzone-filename">${files.length} files selected</span>
         <span style="color:var(--text-muted)"> · ${_formatSize(totalSize)} total</span>`;
    }
    document.getElementById('upload-btn').disabled = false;
    document.getElementById('upload-btn').textContent =
      files.length === 1 ? 'Upload' : `Upload ${files.length} Files`;
  },

  async _doUpload() {
    const files = LogManager._pendingFiles;
    if (!files || files.length === 0) return;

    const btn = document.getElementById('upload-btn');
    btn.disabled = true;

    let succeeded = 0;
    let failed = 0;
    const projectId = App.state.currentProject?.id;

    for (let i = 0; i < files.length; i++) {
      btn.innerHTML = `<div class="spinner spinner-sm"></div> Uploading ${i + 1}/${files.length}…`;
      try {
        await api.uploadLog(projectId, files[i]);
        succeeded++;
      } catch (err) {
        failed++;
        Toast.error(`Failed to upload "${files[i].name}": ${err.message}`);
      }
    }

    Modal.hide();
    if (succeeded > 0) {
      Toast.success(
        succeeded === 1
          ? `Uploaded "${files[0].name}"`
          : `Uploaded ${succeeded} file${succeeded !== 1 ? 's' : ''}`
      );
    }
    LogManager.renderLogFiles();
  },

  async uploadFile(file) {
    const projectId = App.state.currentProject?.id;
    try {
      await api.uploadLog(projectId, file);
      Toast.success(`Uploaded "${file.name}"`);
      LogManager.renderLogFiles();
    } catch (err) {
      Toast.error(`Upload failed: ${err.message}`);
      throw err;
    }
  },

  // ── Add path modal ─────────────────────────────────────────────────────────
  showAddPathModal() {
    const body = `
      <div class="form-group">
        <label class="form-label">Log File Path <span class="required">*</span></label>
        <input id="lp-path" class="form-input" type="text"
               placeholder="/var/log/wso2/wso2carbon.log" autofocus />
        <span class="form-hint">The file will be referenced by path, not copied into the project</span>
      </div>`;

    const footer = `
      <button class="btn btn-ghost" onclick="Modal.hide()">Cancel</button>
      <button class="btn btn-primary" onclick="LogManager.addPath()">Add Reference</button>`;

    Modal.show('Add Log File by Path', body, footer);
  },

  async addPath() {
    const path = document.getElementById('lp-path').value.trim();
    if (!path) { Toast.error('Please enter a file path'); return; }

    const btn = document.querySelector('#modal-footer .btn-primary');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner spinner-sm"></div> Adding…';

    try {
      await api.addLogPath(App.state.currentProject.id, path);
      Modal.hide();
      Toast.success(`Added log reference: ${path.split('/').pop()}`);
      LogManager.renderLogFiles();
    } catch (err) {
      Toast.error(`Failed to add: ${err.message}`);
      btn.disabled = false;
      btn.innerHTML = 'Add Reference';
    }
  },

  // ── Add folder modal ───────────────────────────────────────────────────────
  showAddFolderModal() {
    const body = `
      <div class="form-group">
        <label class="form-label">Folder Path <span class="required">*</span></label>
        <input id="lf-folder" class="form-input" type="text"
               placeholder="/var/log/wso2/" autofocus />
        <span class="form-hint">All .log and .txt files found recursively will be added as references</span>
      </div>`;

    const footer = `
      <button class="btn btn-ghost" onclick="Modal.hide()">Cancel</button>
      <button class="btn btn-primary" onclick="LogManager.addFolder()">Scan Folder</button>`;

    Modal.show('Add Logs from Folder', body, footer);
  },

  async addFolder() {
    const folder = document.getElementById('lf-folder').value.trim();
    if (!folder) { Toast.error('Please enter a folder path'); return; }

    const btn = document.querySelector('#modal-footer .btn-primary');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner spinner-sm"></div> Scanning…';

    try {
      const result = await api.addLogFolder(App.state.currentProject.id, folder);
      Modal.hide();
      if (result.added === 0) {
        Toast.warn('No new log files found in that folder');
      } else {
        Toast.success(`Added ${result.added} log file${result.added !== 1 ? 's' : ''} from folder`);
      }
      LogManager.renderLogFiles();
    } catch (err) {
      Toast.error(`Failed to scan folder: ${err.message}`);
      btn.disabled = false;
      btn.innerHTML = 'Scan Folder';
    }
  },

  // ── Load a log file into the viewer ───────────────────────────────────────
  async _loadFile(logId, projectId, btnEl) {
    _activeLogId = logId;
    // Update active state in sidebar
    document.querySelectorAll('.log-file-item').forEach(el => {
      el.classList.toggle('active', el.dataset.logId === logId);
    });
    await LogViewer.loadFile(logId, projectId);
  },

  // ── Delete log entry ───────────────────────────────────────────────────────
  async deleteLog(logId, filename) {
    const confirmed = window.confirm(`Remove "${filename}" from this project?`);
    if (!confirmed) return;

    try {
      await api.deleteLog(App.state.currentProject.id, logId);
      Toast.success(`Removed "${filename}"`);
      LogManager.renderLogFiles();
    } catch (err) {
      Toast.error(`Failed to remove: ${err.message}`);
    }
  },
};

// ── Private helpers ────────────────────────────────────────────────────────────

let _activeLogId = null;

function _logSidebarItem(log, projectId) {
  const typeLabels = {
    wso2carbon:  'Carbon',
    audit:       'Audit',
    http_access: 'HTTP',
    correlation: 'Correlation',
    generic:     'Generic',
  };
  const typeLabel = typeLabels[log.file_type] || log.file_type;
  const dateRange = _formatDateRange(log.first_timestamp, log.last_timestamp);
  const size = _formatSize(log.size_bytes);

  const item = document.createElement('div');
  item.className = 'log-file-item' + (_activeLogId === log.id ? ' active' : '');
  item.dataset.logId = log.id;

  item.innerHTML = `
    <div class="log-file-item-name" title="${_esc(log.original_path)}">${_esc(log.filename)}</div>
    <div class="log-file-item-meta">
      <span class="badge badge-${log.file_type}" style="font-size:10px">${typeLabel}</span>
      <span>${size}</span>
      ${log.line_count != null ? `<span>${log.line_count.toLocaleString()} lines</span>` : ''}
    </div>
    ${dateRange !== '—' ? `<div class="log-file-item-meta" style="font-size:10px">${_esc(dateRange)}</div>` : ''}
    <div class="log-file-item-actions">
      <button class="btn btn-ghost btn-xs" title="Load in viewer" onclick="event.stopPropagation(); LogManager._loadFile('${log.id}', '${projectId}', this)">Load</button>
      <button class="btn btn-icon btn-danger" style="padding:2px 6px;font-size:11px" title="Remove" onclick="event.stopPropagation(); LogManager.deleteLog('${log.id}', '${_esc(log.filename)}')">✕</button>
    </div>`;

  item.addEventListener('click', () => {
    LogManager._loadFile(log.id, projectId, item.querySelector('.btn-ghost'));
  });

  return item;
}

function _logRow(log) {
  const typeLabel = {
    wso2carbon:  'WSO2 Carbon',
    audit:       'Audit',
    http_access: 'HTTP Access',
    correlation: 'Correlation',
    generic:     'Generic',
  }[log.file_type] || log.file_type;

  const source = log.is_reference ? 'Reference' : 'Uploaded';
  const dateRange = _formatDateRange(log.first_timestamp, log.last_timestamp);

  return `
    <tr>
      <td>
        <div class="log-filename">${_esc(log.filename)}</div>
        <div class="log-path" title="${_esc(log.original_path)}">${_esc(log.original_path)}</div>
      </td>
      <td><span class="badge badge-${log.file_type}">${typeLabel}</span></td>
      <td><span class="log-meta-value">${_formatSize(log.size_bytes)}</span></td>
      <td><span class="log-meta-value">${log.line_count != null ? log.line_count.toLocaleString() : '—'}</span></td>
      <td><span class="log-meta-value" style="font-size:11px">${dateRange}</span></td>
      <td>
        <span class="badge ${log.is_reference ? 'badge-warn' : 'badge-info'}" style="font-size:10px">
          ${source}
        </span>
      </td>
      <td>
        <button class="btn btn-icon btn-danger" title="Remove"
                onclick="LogManager.deleteLog('${log.id}', '${_esc(log.filename)}')">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zm-1 8a1 1 0 112 0v3a1 1 0 11-2 0v-3zm4 0a1 1 0 112 0v3a1 1 0 11-2 0v-3z" clip-rule="evenodd"/>
          </svg>
        </button>
      </td>
    </tr>`;
}

function _formatSize(bytes) {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function _formatDateRange(first, last) {
  if (!first && !last) return '—';
  if (!last || first === last) return first || '—';
  // Shorten if same date prefix
  if (first && last && first.substring(0, 10) === last.substring(0, 10)) {
    return `${first} – ${last.substring(11)}`;
  }
  return `${first} – ${last}`;
}

function _esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
