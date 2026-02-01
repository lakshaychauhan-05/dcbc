import React from 'react';
import { format } from 'date-fns';
import { Message } from '../types/chat';
import { SparklesIcon, UserIcon } from '@heroicons/react/24/outline';

interface MessageBubbleProps {
  message: Message;
  isFirst?: boolean;
  isLast?: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isFirst = true, isLast = true }) => {
  const isUser = message.role === 'user';

  // Format message content with line breaks
  const formatContent = (content: string) => {
    return content.split('\n').map((line, index) => (
      <React.Fragment key={index}>
        {line}
        {index < content.split('\n').length - 1 && <br />}
      </React.Fragment>
    ));
  };

  return (
    <div
      className={`flex items-end gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'} ${
        isFirst ? 'mt-4' : 'mt-1'
      } ${isUser ? 'animate-slide-in-right' : 'animate-slide-in'}`}
    >
      {/* Avatar - only show on last message of a group */}
      {isLast ? (
        <div className={`avatar ${isUser ? 'avatar-user' : 'avatar-bot'} mb-1`}>
          {isUser ? (
            <UserIcon className="w-4 h-4" />
          ) : (
            <SparklesIcon className="w-4 h-4" />
          )}
        </div>
      ) : (
        <div className="w-8" /> // Spacer for alignment
      )}

      {/* Message content */}
      <div className="flex flex-col max-w-[75%]">
        <div
          className={`px-4 py-2.5 ${
            isUser
              ? 'chat-bubble-user text-white'
              : 'chat-bubble-bot text-slate-800'
          }`}
        >
          <p className="message-content">{formatContent(message.content)}</p>
        </div>

        {/* Timestamp and intent - only show on last message */}
        {isLast && (
          <div className={`flex items-center gap-2 mt-1 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
            <span className="text-[11px] text-slate-400">
              {format(message.timestamp, 'HH:mm')}
            </span>

            {/* Intent badge - only for bot messages */}
            {!isUser && message.intent && message.intent.intent !== 'unknown' && (
              <span className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-500 rounded-full">
                {message.intent.intent.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
