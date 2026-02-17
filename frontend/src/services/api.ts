import axios, { AxiosHeaders } from 'axios';
import type { ChatRequest, ChatResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Base API instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Doctor Portal API
export const portalApi = axios.create({
  baseURL: `${API_BASE_URL}/portal`,
});

portalApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('portal_token');
  if (token) {
    const headers = config.headers instanceof AxiosHeaders
      ? config.headers
      : new AxiosHeaders(config.headers);
    headers.set('Authorization', `Bearer ${token}`);
    config.headers = headers;
  }
  return config;
});

portalApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('portal_token');
      window.location.href = '/doctor/login';
    }
    return Promise.reject(error);
  }
);

// Admin Portal API
export const adminApi = axios.create({
  baseURL: `${API_BASE_URL}/admin`,
});

adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    const headers = config.headers instanceof AxiosHeaders
      ? config.headers
      : new AxiosHeaders(config.headers);
    headers.set('Authorization', `Bearer ${token}`);
    config.headers = headers;
  }
  return config;
});

adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_token');
      window.location.href = '/admin/login';
    }
    return Promise.reject(error);
  }
);

// Chatbot API
export const chatService = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>('/chatbot/api/v1/chat/', request);
    return response.data;
  },

  async getConversationHistory(conversationId: string, limit: number = 50) {
    const response = await api.get(`/chatbot/api/v1/chat/conversation/${conversationId}`, {
      params: { limit }
    });
    return response.data;
  },

  async clearConversation(conversationId: string) {
    const response = await api.delete(`/chatbot/api/v1/chat/conversation/${conversationId}`);
    return response.data;
  },

  async healthCheck(): Promise<boolean> {
    try {
      const response = await api.get('/chatbot/api/v1/health/', { timeout: 5000 });
      return response.status === 200;
    } catch {
      return false;
    }
  },
};

// Helper function for normalizing responses.
// Admin /doctors returns a plain array; other endpoints may wrap in { doctors: [...] }.
export function normalizeDoctorsResponse(data: unknown): unknown[] {
  if (data == null) return [];
  if (Array.isArray(data)) return data;
  if (typeof data !== 'object') return [];
  const d = data as Record<string, unknown>;
  const arr = d.doctors ?? (d.data as Record<string, unknown>)?.doctors;
  return Array.isArray(arr) ? arr : [];
}

export default api;
