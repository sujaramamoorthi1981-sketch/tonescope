import type { AnalysisResult, Emotion, HistoryItem, ModelInfo, Stats, User } from "../types";

const TOKEN_KEY = "tonescope_token";
export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) { super(message); }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = tokenStore.get();
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...options,
      headers: {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError("NETWORK_ERROR", "Can't reach the server. Check your connection and try again.", 0);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok || !body?.success) {
    throw new ApiError(body?.error?.code ?? "UNKNOWN", body?.error?.message ?? "Something went wrong.", res.status);
  }
  return body.data as T;
}

export const api = {
  register: (name: string, email: string, password: string) =>
    request<{ token: string; user: User }>("/auth/register", { method: "POST", body: JSON.stringify({ name, email, password }) }),
  login: (email: string, password: string) =>
    request<{ token: string; user: User }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<User>("/auth/me"),
  analyze: (wav: Blob, filename: string) => {
    const form = new FormData();
    form.append("file", wav, filename);
    return request<AnalysisResult>("/analyze", { method: "POST", body: form });
  },
  history: (emotion?: Emotion) => request<HistoryItem[]>(`/history${emotion ? `?emotion=${emotion}` : ""}`),
  deleteAnalysis: (id: number) => request<null>(`/history/${id}`, { method: "DELETE" }),
  stats: () => request<Stats>("/stats"),
  model: () => request<ModelInfo>("/model"),
};
