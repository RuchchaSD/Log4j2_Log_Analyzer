// ── App Controller ─────────────────────────────────────────────────────────────
const App = {
  state: {
    currentProject: null,
    currentTab: 'projects',
  },

  // ── Init ───────────────────────────────────────────────────────────────────
  init() {
    // Tab navigation
    document.querySelectorAll('.nav-item[data-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        if (!btn.disabled) App.switchTab(tab);
      });
    });

    // Load initial data
    ProjectManager.renderRecentProjects();

    // Set initial tab state (all non-project tabs disabled until a project is open)
    App._updateTabAccess();
  },

  // ── Tab switching ──────────────────────────────────────────────────────────
  switchTab(tabName) {
    // Deactivate all
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    // Activate target
    const content = document.getElementById(`tab-${tabName}`);
    if (content) content.classList.add('active');

    const navBtn = document.querySelector(`.nav-item[data-tab="${tabName}"]`);
    if (navBtn) navBtn.classList.add('active');

    App.state.currentTab = tabName;

    // Trigger data loads per tab
    if (tabName === 'projects') {
      ProjectManager.renderRecentProjects();
    } else if (tabName === 'logs' && App.state.currentProject) {
      LogManager.renderLogFiles();
    } else if (tabName === 'settings') {
      FormatManager.renderFormatList();
    } else if (tabName === 'repos') {
      RepoManager.renderRepoList();
    }
  },

  // ── Set current project ────────────────────────────────────────────────────
  setCurrentProject(project) {
    App.state.currentProject = project;
    App._updateProjectHeader(project);
    App._updateTabAccess();
    // Clear viewer state whenever the active project changes
    if (typeof LogViewer !== 'undefined') LogViewer.reset();
  },

  // ── Update header breadcrumb / project badge ───────────────────────────────
  _updateProjectHeader(project) {
    const sep    = document.getElementById('breadcrumb-sep');
    const name   = document.getElementById('breadcrumb-project');
    const badge  = document.getElementById('project-badge');
    const bName  = document.getElementById('project-badge-name');

    if (project) {
      sep.style.display  = '';
      name.textContent   = project.name;
      badge.style.display = '';
      bName.textContent  = project.name;
    } else {
      sep.style.display  = 'none';
      name.textContent   = '';
      badge.style.display = 'none';
    }
  },

  // ── Enable / disable tabs based on project state ──────────────────────────
  _updateTabAccess() {
    const hasProject = !!App.state.currentProject;
    const tabsRequiringProject = ['logs', 'analytics', 'ai'];

    tabsRequiringProject.forEach(tab => {
      const btn = document.querySelector(`.nav-item[data-tab="${tab}"]`);
      if (btn) btn.disabled = !hasProject;
    });
  },
};

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => App.init());
