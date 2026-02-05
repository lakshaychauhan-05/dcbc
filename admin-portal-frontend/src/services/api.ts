import axios, { AxiosHeaders } from "axios";

const API_BASE = import.meta.env.VITE_ADMIN_API_URL || "http://localhost:5050/admin";

const api = axios.create({
  baseURL: API_BASE,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("admin_token");
  if (token) {
    const headers = config.headers instanceof AxiosHeaders ? config.headers : new AxiosHeaders(config.headers);
    headers.set("Authorization", `Bearer ${token}`);
    config.headers = headers;
  }
  return config;
});

// Response interceptor to handle 401 errors (expired/invalid token)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear invalid token and redirect to login
      localStorage.removeItem("admin_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

/** Normalize API list response: handles { doctors: [...] } or { data: { doctors: [...] } } */
export function normalizeDoctorsResponse(data: unknown): any[] {
  if (data == null || typeof data !== "object") return [];
  const d = data as Record<string, unknown>;
  const arr = d.doctors ?? (d.data as Record<string, unknown>)?.doctors;
  return Array.isArray(arr) ? arr : [];
}

export default api;
