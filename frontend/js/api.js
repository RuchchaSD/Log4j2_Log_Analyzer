// Backend API client
const API_BASE = '';

const api = {
  // ── Projects ──────────────────────────────────────────────────────────────
  async createProject(data) {
    return _post('/api/projects', data);
  },
  async listProjects() {
    return _get('/api/projects');
  },
  async getProject(id) {
    return _get(`/api/projects/${id}`);
  },
  async updateProject(id, updates) {
    return _put(`/api/projects/${id}`, updates);
  },
  async deleteProject(id) {
    return _delete(`/api/projects/${id}`);
  },
  async openProject(path) {
    return _post('/api/projects/open', { path });
  },

  // ── Logs ──────────────────────────────────────────────────────────────────
  async uploadLog(projectId, file, formatTypeId) {
    const form = new FormData();
    form.append('file', file);
    let url = `/api/logs/upload?project_id=${projectId}`;
    if (formatTypeId) url += `&format_type_id=${encodeURIComponent(formatTypeId)}`;
    const res = await fetch(url, { method: 'POST', body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },
  async addLogPath(projectId, path, formatTypeId) {
    let url = `/api/logs/path?project_id=${projectId}`;
    if (formatTypeId) url += `&format_type_id=${encodeURIComponent(formatTypeId)}`;
    return _post(url, { path });
  },
  async addLogFolder(projectId, folder, formatTypeId) {
    let url = `/api/logs/folder?project_id=${projectId}`;
    if (formatTypeId) url += `&format_type_id=${encodeURIComponent(formatTypeId)}`;
    return _post(url, { folder });
  },
  async setLogFormat(projectId, logId, formatTypeId) {
    return _put(`/api/logs/${logId}/format?project_id=${projectId}`, { format_type_id: formatTypeId || null });
  },
  async listLogs(projectId) {
    return _get(`/api/logs?project_id=${projectId}`);
  },
  async deleteLog(projectId, logId) {
    return _delete(`/api/logs/${logId}?project_id=${projectId}`);
  },

  // ── Parsing / Log Viewer ───────────────────────────────────────────────────
  async getLogEntries(projectId, logId, offset = 0, limit = 300) {
    return _get(`/api/logs/${logId}/entries?project_id=${projectId}&offset=${offset}&limit=${limit}`);
  },
  async getLogSummary(projectId, logId) {
    return _get(`/api/logs/${logId}/summary?project_id=${projectId}`);
  },
  async filterLog(projectId, logId, body) {
    return _post(`/api/logs/${logId}/filter?project_id=${projectId}`, body);
  },
  async getLogGroups(projectId, logId, groupBy) {
    return _get(`/api/logs/${logId}/groups/${groupBy}?project_id=${projectId}`);
  },
  async searchLogs(projectId, body) {
    return _post(`/api/logs/search?project_id=${projectId}`, body);
  },

  // ── Format types ───────────────────────────────────────────────────────────
  async listFormats() {
    return _get('/api/formats');
  },
  async createFormat(data) {
    return _post('/api/formats', data);
  },
  async updateFormat(id, updates) {
    return _put(`/api/formats/${id}`, updates);
  },
  async deleteFormat(id) {
    return _delete(`/api/formats/${id}`);
  },
  async testFormatPattern(pattern, line) {
    return _post('/api/formats/test', { pattern, line });
  },

  // ── Repos (Sprint 3) ───────────────────────────────────────────────────────
  async listRepos() {
    return _get('/api/repos');
  },
  async createRepo(data) {
    return _post('/api/repos', data);
  },
  async deleteRepo(id) {
    return _delete(`/api/repos/${id}`);
  },
  async reindexRepo(id) {
    return _post(`/api/repos/${id}/reindex`, {});
  },
  async repoStatus(id) {
    return _get(`/api/repos/${id}/status`);
  },
  async resolveRepo(packageName) {
    return _post('/api/repos/resolve', { packageName });
  },
  async listFeatures() {
    return _get('/api/features');
  },
  async resolveStackTrace(stackTrace) {
    return _post('/api/stacktrace/resolve', { stackTrace });
  },
  async readSource(path, line, context = 10) {
    const params = new URLSearchParams({ path });
    if (line != null) params.set('line', line);
    params.set('context', context);
    return _get(`/api/files/source?${params.toString()}`);
  },
};

// ── HTTP helpers ─────────────────────────────────────────────────────────────

async function _get(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

async function _post(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

async function _put(url, data) {
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

async function _delete(url) {
  const res = await fetch(url, { method: 'DELETE' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}
