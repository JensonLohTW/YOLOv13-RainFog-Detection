import { useAuthStore } from "@/stores/auth-store";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type ApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
};

function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Token ${token}` } : {};
}

async function unwrapResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const payload = (await response.json()) as ApiEnvelope<unknown>;
      if (payload.message) message = payload.message;
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(message);
  }
  const payload = (await response.json()) as ApiEnvelope<T>;
  return payload.data;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: getAuthHeaders(),
  });
  return unwrapResponse<T>(response);
}

export async function apiPost<T, P>(path: string, body: P): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
  });
  return unwrapResponse<T>(response);
}

export async function apiPut<T, P>(path: string, body: P): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
  });
  return unwrapResponse<T>(response);
}

export async function apiUpload<T>(path: string, file: File, fieldName = "image"): Promise<T> {
  const formData = new FormData();
  formData.append(fieldName, file);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });
  return unwrapResponse<T>(response);
}
