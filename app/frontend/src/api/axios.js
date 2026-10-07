export const API_BASE = 'http://localhost:8000';

async function fetchWrapper(url, options = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const response = await fetch(`${API_BASE}${url}`, { ...options, headers });
  let data;
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok) {
    throw new Error(data.detail || data.message || 'Something went wrong');
  }
  return data;
}

const api = {
  get: (url) => fetchWrapper(url, { method: 'GET' }),
  post: (url, body) => fetchWrapper(url, { method: 'POST', body: JSON.stringify(body) }),
  put: (url, body) => fetchWrapper(url, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (url) => fetchWrapper(url, { method: 'DELETE' }),
};

export default api;
