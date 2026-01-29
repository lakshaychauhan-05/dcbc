import axios from 'axios';
import { ChatRequest, ChatResponse } from '../types/chat';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8003';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const chatService = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await api.post<ChatResponse>('/api/v1/chat/', request);
      return response.data;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  },

  async getConversationHistory(conversationId: string, limit: number = 50) {
    try {
      const response = await api.get(`/api/v1/chat/conversation/${conversationId}`, {
        params: { limit }
      });
      return response.data;
    } catch (error) {
      console.error('Error getting conversation history:', error);
      throw error;
    }
  },

  async clearConversation(conversationId: string) {
    try {
      const response = await api.delete(`/api/v1/chat/conversation/${conversationId}`);
      return response.data;
    } catch (error) {
      console.error('Error clearing conversation:', error);
      throw error;
    }
  },

  async confirmAction(conversationId: string, actionData?: any) {
    try {
      const response = await api.post(`/api/v1/chat/conversation/${conversationId}/confirm`, actionData);
      return response.data;
    } catch (error) {
      console.error('Error confirming action:', error);
      throw error;
    }
  },
};