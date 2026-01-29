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

export default api;
