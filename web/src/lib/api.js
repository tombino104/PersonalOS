export class ApiError extends Error {
  constructor(status, code, message, retryAfter = null) {
    super(message);
    this.status = status;
    this.code = code;
    this.retryAfter = retryAfter;
  }
}

let onUnauthorized = () => {};

export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

async function request(method, path, body) {
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin',
  });
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    const error = data?.error ?? {};
    if (response.status === 401 && error.code === 'unauthorized') onUnauthorized();
    const retryAfter = Number(response.headers.get('Retry-After')) || null;
    throw new ApiError(response.status, error.code ?? 'error', error.message ?? response.statusText, retryAfter);
  }
  return data;
}

export function pluginRequest(pluginId, method, path, body) {
  return request(method, `/plugins/${pluginId}${path}`, body);
}

const query = (params) => new URLSearchParams(params).toString();
const range = (from, to) => `?${query({ from, to })}`;

export const api = {
  me: () => request('GET', '/auth/me'),
  authStatus: () => request('GET', '/auth/status'),
  setup: (code, name, password) => request('POST', '/auth/setup', { code, name, password }),
  reset: (code, name, password) => request('POST', '/auth/reset', { code, name, password }),
  login: (name, password) => request('POST', '/auth/login', { name, password }),
  logout: () => request('POST', '/auth/logout'),
  changePassword: (current_password, new_password) =>
    request('POST', '/auth/password', { current_password, new_password }),

  today: () => request('GET', '/today'),
  areas: () => request('GET', '/areas'),

  activities: (includeArchived = false) =>
    request('GET', `/activities?${query({ include_archived: includeArchived })}`),
  createActivity: (activity) => request('POST', '/activities', activity),
  updateActivity: (id, changes) => request('PATCH', `/activities/${id}`, changes),

  openReport: (day) => request('POST', '/reports', { day }),
  getReport: (day) => request('GET', `/reports/${day}`),
  listReports: (from, to) => request('GET', `/reports${range(from, to)}`),
  setCompletion: (day, activityId, done) =>
    request('PUT', `/reports/${day}/completions/${activityId}`, { done }),
  setReflection: (day, text) => request('PUT', `/reports/${day}/reflection`, { text }),
  syncReport: (day) => request('POST', `/reports/${day}/sync`),
  completeReport: (day) => request('POST', `/reports/${day}/complete`),

  plugins: () => request('GET', '/plugins'),
  activatePlugin: (id) => request('POST', `/plugins/${id}/activate`, { accept_permissions: true }),
  deactivatePlugin: (id) => request('POST', `/plugins/${id}/deactivate`),
  removePluginData: (id, confirm) => request('POST', `/plugins/${id}/remove-data`, { confirm }),

  scores: (from, to) => request('GET', `/scores${range(from, to)}`),
  areaStats: (from, to) => request('GET', `/stats/areas${range(from, to)}`),
  activityStats: (from, to) => request('GET', `/stats/activities${range(from, to)}`),
};
