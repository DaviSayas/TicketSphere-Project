// HTTP wrapper around fetch — adds the JWT automatically and handles 401.
import { auth } from './auth.js';

const API_BASE = '';  // same-origin: backend serves the frontend

async function request(method, path, { body, params, headers, raw } = {}) {
  let url = API_BASE + path;
  if (params) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') qs.append(k, v);
    }
    const s = qs.toString();
    if (s) url += '?' + s;
  }

  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', ...(headers || {}) },
  };
  const token = auth.getToken();
  if (token) opts.headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) opts.body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(url, opts);
  } catch (err) {
    throw new Error('Erro de rede — o servidor está disponível?');
  }

  if (res.status === 401) {
    auth.clear();
    if (!location.hash.includes('/login')) location.hash = '/login';
    throw new Error('Sessão expirada');
  }

  if (raw) return res; // caller wants the raw Response (used for CSV download)

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      detail = j.detail || JSON.stringify(j);
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get:  (path, params)  => request('GET', path, { params }),
  post: (path, body)    => request('POST', path, { body }),
  put:  (path, body)    => request('PUT', path, { body }),
  del:  (path)          => request('DELETE', path),
  raw:  (path, params)  => request('GET', path, { params, raw: true }),
};

export const API_BASE_URL = API_BASE;
