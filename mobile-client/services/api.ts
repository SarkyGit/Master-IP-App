import { BASE_URL } from '../config/config';

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

const defaultHeaders = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
};

export async function apiGet(path: string) {
  const headers = { ...defaultHeaders } as Record<string, string>;
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  const response = await fetch(`${BASE_URL}${path}`, { headers });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export async function apiPost(path: string, data: Record<string, unknown>) {
  const headers = { ...defaultHeaders } as Record<string, string>;
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}
