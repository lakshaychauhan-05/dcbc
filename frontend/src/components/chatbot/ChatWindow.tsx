import type { RefObject } from 'react';
import MessageBubble from './MessageBubble';
import type { Message } from '../../types';
import { SparklesIcon, CalendarDaysIcon, ClockIcon, UserIcon } from '@heroicons/react/24/outline';

interface ChatWindowProps {
  messages: Message[];
  isTyping: boolean;
  messagesEndRef: RefObject<HTMLDivElement>;
  onQuickAction: (action: string) => void;
}

const ChatWindow = ({ messages, isTyping, messagesEndRef, onQuickAction }: ChatWindowProps) => {
  const quickActions = [
    { icon: CalendarDaysIcon, label: 'Book Appointment', action: 'I want to book an appointment' },
    { icon: ClockIcon, label: 'Check Availability', action: 'Show me available slots' },
    { icon: UserIcon, label: 'Find a Doctor', action: 'Help me find a doctor' },
  ];

  if (messages.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center mb-6 shadow-lg shadow-cyan-500/25">
          <SparklesIcon className="w-10 h-10 text-white" />
        </div>
        <h3 className="text-xl font-semibold text-slate-800 mb-2">
          Welcome to MediBook AI
        </h3>
        <p className="text-slate-500 text-sm mb-8 max-w-xs">
          I can help you book appointments, check availability, and find the right doctor for your needs.
        </p>

        <div className="w-full space-y-3">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">
            Quick Actions
          </p>
          {quickActions.map((item, index) => (
            <button
              key={index}
              onClick={() => onQuickAction(item.action)}
              className="w-full flex items-center gap-3 p-3 rounded-xl bg-white border border-slate-200 hover:border-cyan-300 hover:bg-cyan-50/50 transition-all duration-200 group"
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500/10 to-blue-500/10 flex items-center justify-center group-hover:from-cyan-500/20 group-hover:to-blue-500/20 transition-colors">
                <item.icon className="w-5 h-5 text-cyan-600" />
              </div>
              <span className="text-sm font-medium text-slate-700 group-hover:text-cyan-700 transition-colors">
                {item.label}
              </span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {isTyping && (
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0">
            <SparklesIcon className="w-4 h-4 text-white" />
          </div>
          <div className="bg-white rounded-2xl rounded-tl-md px-4 py-3 shadow-sm border border-slate-100">
            <div className="flex space-x-1.5">
              <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
              <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
              <span className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
            </div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatWindow;
