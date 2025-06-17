import { apiGet } from './api';

export interface Device {
  id: number;
  hostname: string;
  ip: string;
  device_type?: string;
}

export async function fetchDevices(search?: string): Promise<Device[]> {
  let path = '/api/v1/devices';
  if (search) {
    const params = new URLSearchParams({ search });
    path += `?${params.toString()}`;
  }
  return apiGet(path);
}
