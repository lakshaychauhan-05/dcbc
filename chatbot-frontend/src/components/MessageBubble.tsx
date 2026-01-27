import React from 'react';
import { format } from 'date-fns';
import { Message } from '../types/chat';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-xl shadow-sm ${
        isUser
          ? 'bg-secondary-600 text-white ml-auto'
          : 'bg-white text-slate-800 mr-auto border border-slate-200'
      }`}>
        <p className="text-sm leading-relaxed">{message.content}</p>

        {message.intent && message.intent.intent !== 'unknown' && (
          <div className={`mt-2 text-xs px-2 py-1 rounded ${
            isUser
              ? 'bg-secondary-700 text-slate-100'
              : 'bg-slate-100 text-slate-600'
          }`}>
            Intent: {message.intent.intent.replace('_', ' ')}
            {message.intent.confidence && (
              <span className="ml-2">
                ({Math.round(message.intent.confidence * 100)}%)
              </span>
            )}
          </div>
        )}

        <div className={`text-xs mt-1 ${
          isUser ? 'text-slate-100/70' : 'text-slate-500'
        }`}>
          {format(message.timestamp, 'HH:mm')}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;