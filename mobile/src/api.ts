import { User } from 'firebase/auth';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

export type Account = { firebase_uid: string; role: 'caregiver' | 'patient'; display_name: string };
export type Patient = {
  id: string;
  display_name: string;
  linked: boolean;
  relationship_id?: string | null;
};

export async function api<T>(user: User, path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE_URL) throw new Error('API address is missing from the app configuration.');
  const token = await user.getIdToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
