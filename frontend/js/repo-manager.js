// Sprint 3 — Repository registration + stack trace resolution UI
const RepoManager = {
  async renderRepoList() {
    const container = document.getElementById('repo-list');
    if (!container) return;
    container.innerHTML = '<div class="loading-row"><div class="spinner"></div> Loading…</div>';
    try {
      const { repos } = await api.listRepos();
      if (!repos || repos.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">⑃</div>
            <div class="empty-state-title">No repositories registered</div>
            <div class="empty-state-desc">Register a local WSO2 repo checkout to resolve stack traces to source</div>
          </div>`;
        return;
      }
      container.innerHTML = repos.map(r => `
        <div class="format-card" data-repo-id="${r.id}">
          <div class="format-card-body">
            <div class="format-card-title">${_esc(r.label)}</div>
            <div class="format-card-subtitle">${_esc(r.path)}</div>
            <div class="format-card-meta">
              ${r.fileCount || 0} Java files · ${r.classCount || 0} classes
              ${r.lastIndexed ? ` · last indexed ${new Date(r.lastIndexed).toLocaleString()}` : ' · not indexed'}
            </div>
          </div>
          <div class="format-card-actions">
            <button class="btn btn-ghost btn-sm" onclick="RepoManager.reindex('${r.id}')">Reindex</button>
            <button class="btn btn-ghost btn-sm" onclick="RepoManager.remove('${r.id}')">Remove</button>
          </div>
        </div>`).join('');
    } catch (err) {
      container.innerHTML = `<div class="error-row">Failed to load repos: ${_esc(err.message)}</div>`;
    }
  },

  showAddRepoModal() {
    Modal.show({
      title: 'Register Repository',
      body: `
        <div class="form-group">
          <label class="form-label">Label</label>
          <input id="repo-label" class="form-input" placeholder="e.g. identity-inbound-auth-oauth" />
        </div>
        <div class="form-group">
          <label class="form-label">Local path</label>
          <input id="repo-path" class="form-input" placeholder="/Users/you/wso2/identity-inbound-auth-oauth" />
        </div>
        <div class="form-group">
          <label class="form-label">Branch (optional)</label>
          <input id="repo-branch" class="form-input" placeholder="master" />
        </div>
        <div class="form-group">
          <label class="form-label">Remote URL (optional)</label>
          <input id="repo-remote" class="form-input" placeholder="https://github.com/wso2/identity-inbound-auth-oauth" />
        </div>
      `,
      footer: `
        <button class="btn btn-ghost" onclick="Modal.hide()">Cancel</button>
        <button class="btn btn-primary" onclick="RepoManager.submitAddRepo()">Register</button>
      `,
    });
  },

  async submitAddRepo() {
    const label = document.getElementById('repo-label').value.trim();
    const path = document.getElementById('repo-path').value.trim();
    const branch = document.getElementById('repo-branch').value.trim() || null;
    const remoteUrl = document.getElementById('repo-remote').value.trim() || null;
    if (!label || !path) {
      Toast.error('Label and path are required');
      return;
    }
    try {
      const repo = await api.createRepo({ label, path, branch, remoteUrl });
      Modal.hide();
      Toast.success(`Registered ${repo.label}`);
      await this.renderRepoList();
      // Auto-index on first registration
      await this.reindex(repo.id);
    } catch (err) {
      Toast.error(err.message);
    }
  },

  async reindex(id) {
    try {
      Toast.info('Indexing…');
      const repo = await api.reindexRepo(id);
      Toast.success(`Indexed ${repo.fileCount} files, ${repo.classCount} classes`);
      await this.renderRepoList();
    } catch (err) {
      Toast.error(err.message);
    }
  },

  async remove(id) {
    if (!confirm('Unregister this repository? (the on-disk checkout is not deleted)')) return;
    try {
      await api.deleteRepo(id);
      Toast.success('Repository removed');
      await this.renderRepoList();
    } catch (err) {
      Toast.error(err.message);
    }
  },
};

function _esc(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}
