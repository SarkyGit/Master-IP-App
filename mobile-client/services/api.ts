import { BASE_URL } from '../config/config';

const defaultHeaders = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
};

export async function apiGet(path: string) {
  const response = await fetch(`${BASE_URL}${path}`, { headers: defaultHeaders });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}
