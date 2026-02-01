import React, { useState, useRef, useEffect } from 'react';
import { ChatBubbleLeftRightIcon, XMarkIcon, SparklesIcon } from '@heroicons/react/24/outline';
import ChatWindow from './ChatWindow';
import ChatInput from './ChatInput';
import SuggestedActions from './SuggestedActions';
import { Message, ChatResponse } from '../types/chat';
import { chatService } from '../services/chatService';

const Chatbot: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [suggestedActions, setSuggestedActions] = useState<string[]>([]);
  const [isOnline, setIsOnline] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Check connection status periodically
  useEffect(() => {
    const checkStatus = async () => {
      try {
        await chatService.healthCheck();
        setIsOnline(true);
      } catch {
        setIsOnline(false);
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);
    setSuggestedActions([]);

    try {
      const response: ChatResponse = await chatService.sendMessage({
        message,
        conversation_id: conversationId,
      });

      setConversationId(response.conversation_id);

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message,
        timestamp: new Date(response.timestamp),
        intent: response.intent,
        suggestedActions: response.suggested_actions,
      };

      setMessages(prev => [...prev, botMessage]);
      setSuggestedActions(response.suggested_actions || []);

    } catch (error) {
      console.error('Error sending message:', error);

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I apologize, but I encountered a connection issue. Please try again in a moment.',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
      setIsOnline(false);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSuggestedAction = (action: string) => {
    handleSendMessage(action);
  };

  const toggleChat = () => {
    setIsOpen(!isOpen);
  };

  // Closed state - floating button
  if (!isOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={toggleChat}
          className="btn-toggle group relative"
          aria-label="Open chat"
        >
          <div className="absolute -inset-1 bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-2xl blur opacity-30 group-hover:opacity-50 transition duration-300"></div>
          <div className="relative flex items-center justify-center">
            <ChatBubbleLeftRightIcon className="w-7 h-7" />
          </div>
          {/* Notification dot */}
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-white flex items-center justify-center">
            <span className="w-2 h-2 bg-white rounded-full"></span>
          </span>
        </button>
      </div>
    );
  }

  // Open state - chat widget
  return (
    <div className="fixed bottom-6 right-6 z-50 animate-scale-in">
      <div className="bg-white rounded-2xl shadow-2xl w-[380px] h-[600px] flex flex-col overflow-hidden border border-slate-200/50">
        {/* Header */}
        <div className="gradient-primary text-white p-4 relative overflow-hidden">
          {/* Decorative elements */}
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2"></div>
          <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2"></div>

          <div className="relative flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="relative">
                <div className="w-11 h-11 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                  <SparklesIcon className="w-6 h-6" />
                </div>
                {/* Online status */}
                <span className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-cyan-600 ${isOnline ? 'bg-emerald-400' : 'bg-slate-400'}`}></span>
              </div>
              <div>
                <h3 className="font-semibold text-lg leading-tight">MediBook AI</h3>
                <p className="text-sm text-cyan-100 flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-slate-400'}`}></span>
                  {isOnline ? 'Online' : 'Reconnecting...'}
                </p>
              </div>
            </div>
            <button
              onClick={toggleChat}
              className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-white/20 transition-colors duration-200"
              aria-label="Close chat"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 min-h-0 bg-gradient-to-b from-slate-50 to-white">
          <ChatWindow
            messages={messages}
            isTyping={isTyping}
            messagesEndRef={messagesEndRef}
          />
        </div>

        {/* Suggested Actions */}
        {suggestedActions.length > 0 && !isTyping && (
          <SuggestedActions
            actions={suggestedActions}
            onActionSelect={handleSuggestedAction}
          />
        )}

        {/* Input */}
        <ChatInput onSendMessage={handleSendMessage} disabled={isTyping} />
      </div>
    </div>
  );
};

export default Chatbot;
