import axios, { AxiosHeaders } from "axios";

const API_BASE = import.meta.env.VITE_PORTAL_API_URL || "http://localhost:5000/portal";

const api = axios.create({
  baseURL: API_BASE,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("portal_token");
  if (token) {
    const headers =
      config.headers instanceof AxiosHeaders
        ? config.headers
        : new AxiosHeaders(config.headers);

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
      localStorage.removeItem("portal_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
