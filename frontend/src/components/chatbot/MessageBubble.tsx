import { SparklesIcon, UserIcon } from '@heroicons/react/24/outline';
import type { Message } from '../../types';
import { format } from 'date-fns';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble = ({ message }: MessageBubbleProps) => {
  const isUser = message.role === 'user';
  const timestamp = format(new Date(message.timestamp), 'h:mm a');

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser
          ? 'bg-gradient-to-br from-slate-600 to-slate-700'
          : 'bg-gradient-to-br from-cyan-500 to-blue-600'
      }`}>
        {isUser ? (
          <UserIcon className="w-4 h-4 text-white" />
        ) : (
          <SparklesIcon className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-tr-md'
            : 'bg-white text-slate-800 rounded-tl-md shadow-sm border border-slate-100'
        }`}>
          <p className="text-sm whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        </div>
        <p className={`text-xs text-slate-400 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {timestamp}
        </p>
      </div>
    </div>
  );
};

export default MessageBubble;
