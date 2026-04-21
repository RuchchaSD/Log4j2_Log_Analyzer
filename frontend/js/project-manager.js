// Project Manager UI
const ProjectManager = {

  // ── Render recent projects list ────────────────────────────────────────────
  async renderRecentProjects() {
    const container = document.getElementById('recent-projects-list');
    container.innerHTML = '<div class="loading-row"><div class="spinner"></div> Loading projects…</div>';

    try {
      const { projects } = await api.listProjects();

      if (!projects || projects.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">📁</div>
            <div class="empty-state-title">No recent projects</div>
            <div class="empty-state-desc">Create a new project to get started</div>
          </div>`;
        return;
      }

      container.innerHTML = projects.map(p => _projectCard(p)).join('');
    } catch (err) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-title">Failed to load projects</div>
          <div class="empty-state-desc">${err.message}</div>
        </div>`;
    }
  },

  // ── Create project modal ───────────────────────────────────────────────────
  async showCreateProjectModal() {
    const fmtSelect = await _buildProjectFormatSelect(null, null);
    const body = `
      <div class="form-grid">
        <div class="form-group form-grid-full">
          <label class="form-label">Project Name <span class="required">*</span></label>
          <input id="cp-name" class="form-input" type="text" placeholder="e.g. APIM Production Issue" autofocus />
        </div>
        <div class="form-group">
          <label class="form-label">Product <span class="required">*</span></label>
          <select id="cp-product" class="form-select" onchange="ProjectManager._onProductChange()">
            <option value="">Select product…</option>
            <option value="apim">API Manager (APIM)</option>
            <option value="is">Identity Server (IS)</option>
            <option value="mi">Micro Integrator (MI)</option>
            <option value="ei">Enterprise Integrator (EI)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Version <span class="required">*</span></label>
          <input id="cp-version" class="form-input" type="text" placeholder="e.g. 4.3.0" />
        </div>
        <div class="form-group">
          <label class="form-label">Default Log Format</label>
          <div id="cp-format-wrapper">${fmtSelect}</div>
          <span class="form-hint">Applied when loading log files without an explicit format assigned</span>
        </div>
        <div class="form-group">
          <label class="form-label">U2 Level</label>
          <input id="cp-u2" class="form-input" type="text" placeholder="e.g. WUM-35" />
        </div>
        <div class="form-group">
          <label class="form-label">Install Path</label>
          <input id="cp-install" class="form-input" type="text" placeholder="/opt/wso2/apim" />
        </div>
        <div class="form-group form-grid-full">
          <label class="form-label">Project Location <span class="required">*</span></label>
          <input id="cp-path" class="form-input" type="text" placeholder="/Users/you/projects" />
          <span class="form-hint">A folder named after the project will be created here</span>
        </div>
      </div>`;

    const footer = `
      <button class="btn btn-ghost" onclick="Modal.hide()">Cancel</button>
      <button class="btn btn-primary" onclick="ProjectManager.createProject()">Create Project</button>`;

    Modal.show('New Project', body, footer);
  },

  // Auto-suggest default format when product changes
  _onProductChange() {
    const product = document.getElementById('cp-product').value;
    const sel = document.querySelector('#cp-format-wrapper select');
    if (!sel) return;
    const suggest = { apim: 'builtin-tid', is: 'builtin-tid', mi: 'builtin-bracket', ei: 'builtin-bracket' }[product];
    if (suggest) sel.value = suggest;
  },

  // ── Create project ─────────────────────────────────────────────────────────
  async createProject() {
    const name    = document.getElementById('cp-name').value.trim();
    const product = document.getElementById('cp-product').value;
    const version = document.getElementById('cp-version').value.trim();
    const path    = document.getElementById('cp-path').value.trim();
    const u2Level = document.getElementById('cp-u2').value.trim() || undefined;
    const install = document.getElementById('cp-install').value.trim() || undefined;
    const fmtSel  = document.querySelector('#cp-format-wrapper select');
    const defaultFormatTypeId = fmtSel ? (fmtSel.value || null) : null;

    if (!name)    { Toast.error('Project name is required'); return; }
    if (!product) { Toast.error('Please select a product'); return; }
    if (!version) { Toast.error('Version is required'); return; }
    if (!path)    { Toast.error('Project location is required'); return; }

    const createBtn = document.querySelector('#modal-footer .btn-primary');
    createBtn.disabled = true;
    createBtn.innerHTML = '<div class="spinner spinner-sm"></div> Creating…';

    try {
      const project = await api.createProject({
        name, product, productVersion: version, path,
        u2Level, installPath: install,
        settings: { defaultFormatTypeId },
      });
      Modal.hide();
      Toast.success(`Project "${project.name}" created successfully`);
      App.setCurrentProject(project);
      ProjectManager.renderRecentProjects();
      App.switchTab('logs');
    } catch (err) {
      Toast.error(`Failed to create project: ${err.message}`);
      createBtn.disabled = false;
      createBtn.innerHTML = 'Create Project';
    }
  },

  // ── Edit project modal ─────────────────────────────────────────────────────
  async showEditProjectModal(project) {
    const currentFmt = project.settings?.defaultFormatTypeId || null;
    const fmtSelect  = await _buildProjectFormatSelect(currentFmt, null);
    const body = `
      <div class="form-grid">
        <div class="form-group form-grid-full">
          <label class="form-label">Project Name <span class="required">*</span></label>
          <input id="ep-name" class="form-input" type="text" value="${_esc(project.name)}" />
        </div>
        <div class="form-group">
          <label class="form-label">Version</label>
          <input id="ep-version" class="form-input" type="text" value="${_esc(project.productVersion)}" />
        </div>
        <div class="form-group">
          <label class="form-label">Default Log Format</label>
          <div id="ep-format-wrapper">${fmtSelect}</div>
          <span class="form-hint">Applied when loading log files without an explicit format assigned</span>
        </div>
        <div class="form-group">
          <label class="form-label">U2 Level</label>
          <input id="ep-u2" class="form-input" type="text" value="${_esc(project.u2Level || '')}" />
        </div>
        <div class="form-group">
          <label class="form-label">Install Path</label>
          <input id="ep-install" class="form-input" type="text" value="${_esc(project.installPath || '')}" />
        </div>
      </div>`;

    const footer = `
      <button class="btn btn-ghost" onclick="Modal.hide()">Cancel</button>
      <button class="btn btn-primary" onclick="ProjectManager.saveEditProject('${project.id}')">Save Changes</button>`;

    Modal.show('Edit Project', body, footer);
  },

  // ── Save edit project ──────────────────────────────────────────────────────
  async saveEditProject(projectId) {
    const name    = document.getElementById('ep-name').value.trim();
    const version = document.getElementById('ep-version').value.trim();
    const u2Level = document.getElementById('ep-u2').value.trim() || null;
    const install = document.getElementById('ep-install').value.trim() || null;
    const fmtSel  = document.querySelector('#ep-format-wrapper select');
    const defaultFormatTypeId = fmtSel ? (fmtSel.value || null) : null;

    if (!name) { Toast.error('Project name is required'); return; }

    const saveBtn = document.querySelector('#modal-footer .btn-primary');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<div class="spinner spinner-sm"></div> Saving…';

    try {
      const updated = await api.updateProject(projectId, {
        name,
        productVersion: version || undefined,
        u2Level,
        installPath: install,
        settings: { defaultFormatTypeId },
      });
      Modal.hide();
      Toast.success('Project updated');
      App.setCurrentProject(updated);
      ProjectManager.renderRecentProjects();
    } catch (err) {
      Toast.error(`Failed to save: ${err.message}`);
      saveBtn.disabled = false;
      saveBtn.innerHTML = 'Save Changes';
    }
  },

  // ── Open existing project modal ────────────────────────────────────────────
  showOpenProjectModal() {
    const body = `
      <div class="form-group">
        <label class="form-label">Project Folder Path <span class="required">*</span></label>
        <input id="op-path" class="form-input" type="text"
               placeholder="/Users/you/projects/MyProject" autofocus />
        <span class="form-hint">Path to the folder containing the .wso2analyzer directory</span>
      </div>`;

    const footer = `
      <button class="btn btn-ghost" onclick="Modal.hide()">Cancel</button>
      <button class="btn btn-primary" onclick="ProjectManager.openProjectByPath()">Open Project</button>`;

    Modal.show('Open Existing Project', body, footer);
  },

  // ── Open project by path ───────────────────────────────────────────────────
  async openProjectByPath() {
    const path = document.getElementById('op-path').value.trim();
    if (!path) { Toast.error('Please enter a project path'); return; }

    const btn = document.querySelector('#modal-footer .btn-primary');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner spinner-sm"></div> Opening…';

    try {
      const project = await api.openProject(path);
      Modal.hide();
      Toast.success(`Opened project "${project.name}"`);
      App.setCurrentProject(project);
      ProjectManager.renderRecentProjects();
      App.switchTab('logs');
    } catch (err) {
      Toast.error(`Failed to open project: ${err.message}`);
      btn.disabled = false;
      btn.innerHTML = 'Open Project';
    }
  },

  // ── Open project from card click ───────────────────────────────────────────
  async openProject(project) {
    try {
      const opened = await api.openProject(project.path);
      App.setCurrentProject(opened);
      App.switchTab('logs');
      Toast.info(`Switched to project "${opened.name}"`);
    } catch (err) {
      Toast.error(`Failed to open project: ${err.message}`);
    }
  },

  // ── Delete project ─────────────────────────────────────────────────────────
  async deleteProject(id, name) {
    const confirmed = window.confirm(
      `Delete project "${name}"?\n\nThis will remove the .wso2analyzer folder and all project data. Log files will NOT be deleted.`
    );
    if (!confirmed) return;

    try {
      await api.deleteProject(id);
      Toast.success(`Project "${name}" deleted`);

      // If this was the current project, clear it
      if (App.state.currentProject && App.state.currentProject.id === id) {
        App.setCurrentProject(null);
        App.switchTab('projects');
      }
      ProjectManager.renderRecentProjects();
    } catch (err) {
      Toast.error(`Failed to delete: ${err.message}`);
    }
  },
};

// ── Private helpers ────────────────────────────────────────────────────────────

function _projectCard(p) {
  const productLabel = { apim: 'API Manager', is: 'Identity Server', mi: 'Micro Integrator', ei: 'Enterprise Integrator' }[p.product] || p.product.toUpperCase();
  const date = new Date(p.updated || p.created).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  const pJson = JSON.stringify(p).replace(/"/g, '&quot;');

  return `
    <div class="project-card" onclick="ProjectManager.openProject(${pJson})">
      <div class="project-card-header">
        <div class="project-card-title">${_esc(p.name)}</div>
        <div class="project-card-actions">
          <button class="btn btn-icon" title="Edit project"
                  onclick="event.stopPropagation(); ProjectManager.showEditProjectModal(${pJson})">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
            </svg>
          </button>
          <button class="btn btn-icon btn-danger" title="Delete project"
                  onclick="event.stopPropagation(); ProjectManager.deleteProject('${p.id}', '${_esc(p.name)}')">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zm-1 8a1 1 0 112 0v3a1 1 0 11-2 0v-3zm4 0a1 1 0 112 0v3a1 1 0 11-2 0v-3z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="project-card-meta">
        <span class="badge badge-${p.product}">${productLabel}</span>
        <span class="badge badge-info">v${_esc(p.productVersion)}</span>
        ${p.u2Level ? `<span class="badge badge-warn">${_esc(p.u2Level)}</span>` : ''}
      </div>
      <div class="project-card-path" title="${_esc(p.path)}">${_esc(p.path)}</div>
      <div style="font-size:11px;color:var(--text-muted)">Updated ${date}</div>
    </div>`;
}

function _esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function _buildProjectFormatSelect(selectedId, _unused) {
  let formats = [];
  try {
    const data = await api.listFormats();
    formats = data.formats || [];
  } catch (_) {}

  const opts = formats.map(f => {
    const sel = selectedId === f.id ? ' selected' : '';
    const label = f.is_builtin ? f.name : `${f.name} (custom)`;
    return `<option value="${_esc(f.id)}"${sel}>${_esc(label)}</option>`;
  }).join('');

  return `<select id="project-default-format" class="form-select">
    <option value="">— None (auto-detect) —</option>
    ${opts}
  </select>`;
}
