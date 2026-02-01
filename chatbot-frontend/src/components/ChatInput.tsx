import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { PaperAirplaneIcon } from '@heroicons/react/24/solid';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = "Type your message..."
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const isMessageEmpty = !message.trim();

  return (
    <div className="border-t border-slate-100 bg-white p-4">
      <form onSubmit={handleSubmit} className="flex items-end gap-3">
        {/* Input container */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="w-full px-4 py-3 bg-slate-50 border border-slate-200 text-slate-800 placeholder-slate-400 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500 focus:bg-white transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ minHeight: '48px', maxHeight: '120px' }}
          />
        </div>

        {/* Send button */}
        <button
          type="submit"
          disabled={isMessageEmpty || disabled}
          className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-200 ${
            isMessageEmpty || disabled
              ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-cyan-500 to-cyan-600 text-white shadow-lg shadow-cyan-500/25 hover:shadow-xl hover:shadow-cyan-500/30 hover:from-cyan-600 hover:to-cyan-700 active:scale-95'
          }`}
          aria-label="Send message"
        >
          <PaperAirplaneIcon className={`w-5 h-5 transition-transform duration-200 ${!isMessageEmpty && !disabled ? '-rotate-45' : ''}`} />
        </button>
      </form>

      {/* Helper text */}
      <div className="flex items-center justify-center mt-2">
        <span className="text-[11px] text-slate-400">
          Press <kbd className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-500 font-medium">Enter</kbd> to send
        </span>
      </div>
    </div>
  );
};

export default ChatInput;
