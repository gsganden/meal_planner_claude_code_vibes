import React, { useState, useRef, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ConnectionStatus } from './ConnectionStatus';
import { Message, ChatMessage, RecipeUpdate } from '@/lib/websocket';

interface RecipeChatProps {
  recipeId: string;
  onRecipeUpdate?: (recipeData: any) => void;
  className?: string;
}

export function RecipeChat({ recipeId, onRecipeUpdate, className = '' }: RecipeChatProps) {
  const { state, messages, sendMessage, lastRecipeUpdate, error, reconnect } = useWebSocket(recipeId);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Notify parent of recipe updates
  useEffect(() => {
    if (lastRecipeUpdate?.payload.recipe_data && onRecipeUpdate) {
      onRecipeUpdate(lastRecipeUpdate.payload.recipe_data);
    }
  }, [lastRecipeUpdate, onRecipeUpdate]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && state === 'authenticated') {
      sendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const isDisabled = state !== 'authenticated';

  const getMessageContent = (message: Message): string => {
    switch (message.type) {
      case 'chat_message':
        return message.payload.content || '';
      case 'recipe_update':
        return message.payload.content || 'Recipe updated';
      case 'error':
        return `Error: ${message.payload.message || 'Unknown error'}`;
      default:
        return '';
    }
  };

  const isUserMessage = (message: Message): boolean => {
    // User messages are chat_messages that don't have a request_id in a following recipe_update
    if (message.type !== 'chat_message') return false;
    
    const messageIndex = messages.indexOf(message);
    const nextMessage = messages[messageIndex + 1];
    
    // If the next message is a recipe_update with this message's ID as request_id, it's a user message
    return !nextMessage || 
           nextMessage.type !== 'recipe_update' || 
           nextMessage.payload.request_id !== message.id;
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Recipe Assistant</h3>
        <ConnectionStatus state={state} />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200 p-3 rounded-lg flex items-center justify-between">
            <span>{error}</span>
            {state === 'error' && (
              <button
                onClick={reconnect}
                className="text-sm underline hover:no-underline"
              >
                Retry
              </button>
            )}
          </div>
        )}

        {messages.map((message) => {
          const content = getMessageContent(message);
          if (!content) return null;

          const isUser = isUserMessage(message);

          return (
            <div
              key={message.id}
              className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] p-3 rounded-lg ${
                  isUser
                    ? 'bg-blue-500 text-white'
                    : message.type === 'error'
                    ? 'bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-200'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                }`}
              >
                <p className="whitespace-pre-wrap">{content}</p>
                <time className={`text-xs mt-1 block ${
                  isUser ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'
                }`}>
                  {new Date(message.timestamp).toLocaleTimeString()}
                </time>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isDisabled}
            placeholder={
              state === 'authenticated'
                ? 'Ask about the recipe...'
                : state === 'authenticating'
                ? 'Authenticating...'
                : state === 'connecting'
                ? 'Connecting...'
                : 'Not connected'
            }
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                     bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100
                     focus:outline-none focus:ring-2 focus:ring-blue-500 
                     disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={isDisabled || !inputValue.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg 
                     hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}