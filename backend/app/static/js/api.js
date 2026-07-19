const API_BASE = '';

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function detailMessage(payload, fallback) {
  if (!payload) return fallback;
  if (typeof payload.detail === 'string') return payload.detail;
  if (typeof payload.message === 'string') return payload.message;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg || JSON.stringify(item)).join('; ');
  }
  return fallback;
}

async function apiFetch(path, options = {}) {
  const request = { ...options };
  request.headers = new Headers(options.headers || {});
  if (request.body !== undefined && !request.headers.has('Content-Type')) {
    request.headers.set('Content-Type', 'application/json');
  }

  let response;
  try {
    response = await fetch(API_BASE + path, request);
  } catch (error) {
    throw new ApiError(`无法连接后端：${error.message || error}`);
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      detailMessage(payload, `请求失败：HTTP ${response.status}`),
      response.status,
    );
  }
  return payload;
}

function queryString(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) {
      query.set(key, String(value));
    }
  });
  return query.toString();
}

export function getWorks({ q = '', status = 'active', tag = '', page = 1, pageSize = 60 } = {}) {
  const query = queryString({ q, status, tag, page, page_size: pageSize });
  return apiFetch(`/api/works?${query}`);
}

export function getWork(seriesId) {
  return apiFetch(`/api/works/${encodeURIComponent(seriesId)}`);
}

export function getEpisodes(workId) {
  return apiFetch(`/api/v1/works/${encodeURIComponent(workId)}/episodes`);
}

export function getStats() {
  return apiFetch('/api/stats');
}

export function getStatus() {
  return apiFetch('/api/status');
}

export function getTasks({ limit = 100 } = {}) {
  return apiFetch(`/api/tasks?${queryString({ limit })}`);
}

export function getTask(taskId) {
  return apiFetch(`/api/tasks/${encodeURIComponent(taskId)}`);
}

export function retryTask(taskId) {
  return apiFetch(`/api/v1/tasks/${encodeURIComponent(taskId)}/retry`, { method: 'POST' });
}

export function importCatalog(payload, source = 'novelquick') {
  const query = queryString({ source });
  return apiFetch(`/api/v1/imports/catalog?${query}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
