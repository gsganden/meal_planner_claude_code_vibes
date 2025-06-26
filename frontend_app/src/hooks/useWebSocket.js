import { useState, useEffect, useCallback, useRef } from 'react';
import { WebSocketManager } from '../lib/websocket';

export function useWebSocket(recipeId) {
  const [state, setState] = useState('disconnected');
  const [messages, setMessages] = useState([]);
  const [lastRecipeUpdate, setLastRecipeUpdate] = useState(null);
  const [error, setError] = useState(null);
  
  const wsManagerRef = useRef(null);
  const messagesRef = useRef([]);

  useEffect(() => {
    if (!recipeId) return;

    // Create WebSocket manager instance
    const wsUrl = import.meta.env.VITE_WS_URL || 'wss://recipe-chat-assistant--fastapi-app.modal.run';
    const manager = new WebSocketManager(wsUrl);
    wsManagerRef.current = manager;

    // Set up event handlers
    manager.on('state', (newState) => {
      setState(newState);
      if (newState === 'error') {
        setError('Connection error. Please try again.');
      } else if (newState === 'authenticated') {
        setError(null);
      }
    });

    manager.on('message', (message) => {
      // Add message to history
      const newMessages = [...messagesRef.current, message];
      messagesRef.current = newMessages;
      setMessages(newMessages);

      // Track last recipe update
      if (message.type === 'recipe_update') {
        setLastRecipeUpdate(message);
      }

      // Handle errors
      if (message.type === 'error') {
        setError(message.payload.message || 'An error occurred');
      }
    });

    // Connect to WebSocket
    manager.connect(recipeId);

    // Cleanup on unmount or recipe change
    return () => {
      manager.disconnect();
      wsManagerRef.current = null;
      messagesRef.current = [];
    };
  }, [recipeId]);

  const sendMessage = useCallback((content) => {
    if (!wsManagerRef.current) {
      setError('Not connected. Please wait...');
      return;
    }

    // Add user message to history immediately for optimistic UI
    const userMessage = {
      type: 'chat_message',
      id: `msg_${Date.now()}`,
      timestamp: new Date().toISOString(),
      payload: { content }
    };
    
    const newMessages = [...messagesRef.current, userMessage];
    messagesRef.current = newMessages;
    setMessages(newMessages);

    // Send via WebSocket
    wsManagerRef.current.sendChatMessage(content);
  }, []);

  const reconnect = useCallback(() => {
    if (wsManagerRef.current && recipeId) {
      wsManagerRef.current.disconnect();
      wsManagerRef.current.connect(recipeId);
    }
  }, [recipeId]);

  return {
    state,
    messages,
    sendMessage,
    lastRecipeUpdate,
    error,
    reconnect
  };
}