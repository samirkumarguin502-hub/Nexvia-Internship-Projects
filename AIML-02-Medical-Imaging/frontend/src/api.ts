const BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8001/api/v1";

export const API_BASE = BASE;

export function authHeaders(): HeadersInit {
  const token = localStorage.getItem("medai_access_token");

  return token
    ? { Authorization: `Bearer ${token}` }
    : {};
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`API ${response.status}: ${message}`);
  }

  return response.json() as Promise<T>;
}

export async function api<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const isFormData = init.body instanceof FormData;

  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...authHeaders(),
      ...init.headers,
    },
  });

  return parseResponse<T>(response);
}

export async function uploadAndAnalyze<T>(file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);

  return api<T>("/inference/analyze", {
    method: "POST",
    body: formData,
  });
}

export async function fetchProtectedImage(
  path: string
): Promise<string> {
  const apiRoot = BASE.replace(/\/api\/v1\/?$/, "");

  const url = path.startsWith("http")
    ? path
    : path.startsWith("/api/v1/")
      ? `${apiRoot}${path}`
      : `${BASE}${path.startsWith("/") ? path : `/${path}`}`;

  const response = await fetch(url, {
    headers: authHeaders(),
  });

  if (!response.ok) {
    throw new Error(
      `Image request failed (${response.status}): ${await response.text()}`
    );
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}