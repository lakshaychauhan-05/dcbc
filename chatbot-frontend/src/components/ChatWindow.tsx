import React from 'react';
import { Message } from '../types/chat';
import MessageBubble from './MessageBubble';
import { CalendarDaysIcon, ClockIcon, UserGroupIcon, SparklesIcon } from '@heroicons/react/24/outline';

interface ChatWindowProps {
  messages: Message[];
  isTyping: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement>;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ messages, isTyping, messagesEndRef }) => {
  // Welcome screen quick actions
  const quickActions = [
    { icon: CalendarDaysIcon, label: 'Book Appointment', color: 'from-cyan-500 to-cyan-600' },
    { icon: ClockIcon, label: 'Check Availability', color: 'from-indigo-500 to-indigo-600' },
    { icon: UserGroupIcon, label: 'Find a Doctor', color: 'from-emerald-500 to-emerald-600' },
  ];

  return (
    <div className="h-full overflow-y-auto p-4 scrollbar-thin">
      {messages.length === 0 ? (
        // Welcome Screen
        <div className="h-full flex flex-col items-center justify-center px-4 animate-slide-up">
          {/* Animated icon */}
          <div className="relative mb-6">
            <div className="w-20 h-20 rounded-2xl gradient-primary flex items-center justify-center animate-float shadow-lg shadow-cyan-500/20">
              <SparklesIcon className="w-10 h-10 text-white" />
            </div>
            <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-emerald-500 rounded-lg flex items-center justify-center border-2 border-white">
              <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
          </div>

          {/* Welcome text */}
          <h3 className="text-xl font-semibold text-slate-800 mb-2 text-center">
            Welcome to MediBook AI
          </h3>
          <p className="text-sm text-slate-500 text-center mb-8 max-w-[280px] leading-relaxed">
            Your intelligent assistant for scheduling medical appointments. How can I help you today?
          </p>

          {/* Quick action cards */}
          <div className="w-full space-y-3">
            {quickActions.map((action, index) => (
              <button
                key={index}
                className="w-full flex items-center gap-4 p-4 bg-white rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-md transition-all duration-200 group text-left"
                onClick={() => {
                  // This will be handled by parent, but we need to trigger the action
                  const event = new CustomEvent('quickAction', { detail: action.label.toLowerCase() });
                  window.dispatchEvent(event);
                }}
              >
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${action.color} flex items-center justify-center group-hover:scale-110 transition-transform duration-200`}>
                  <action.icon className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900">
                    {action.label}
                  </span>
                </div>
                <svg className="w-5 h-5 text-slate-400 group-hover:text-slate-600 group-hover:translate-x-1 transition-all duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            ))}
          </div>

          {/* Hint text */}
          <p className="text-xs text-slate-400 mt-6 text-center">
            Or type your message below to get started
          </p>
        </div>
      ) : (
        // Messages list
        <div className="space-y-1">
          {messages.map((message, index) => (
            <MessageBubble
              key={message.id}
              message={message}
              isFirst={index === 0 || messages[index - 1]?.role !== message.role}
              isLast={index === messages.length - 1 || messages[index + 1]?.role !== message.role}
            />
          ))}

          {/* Typing indicator */}
          {isTyping && (
            <div className="flex items-start gap-3 animate-slide-in">
              <div className="avatar avatar-bot">
                <SparklesIcon className="w-4 h-4" />
              </div>
              <div className="chat-bubble-bot px-4 py-3 flex items-center gap-1">
                <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full"></span>
                <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full"></span>
                <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full"></span>
              </div>
            </div>
          )}
        </div>
      )}

      <div ref={messagesEndRef} className="h-4" />
    </div>
  );
};

export default ChatWindow;
