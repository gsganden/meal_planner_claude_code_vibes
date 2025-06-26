import { useState, useEffect, useCallback, useRef } from 'react';
import { WebSocketManager } from '../lib/websocket';
import { WS_BASE_URL } from '../config/api';

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
    try {
      const manager = new WebSocketManager(WS_BASE_URL);
      wsManagerRef.current = manager;
    } catch (error) {
      console.error('Failed to create WebSocket manager:', error);
      setError('Failed to initialize WebSocket connection');
      return;
    }

    // Set up event handlers
    wsManagerRef.current.on('state', (newState) => {
      setState(newState);
      if (newState === 'error') {
        setError('Connection error. Please try again.');
      } else if (newState === 'authenticated') {
        setError(null);
      }
    });

    wsManagerRef.current.on('message', (message) => {
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
    wsManagerRef.current.connect(recipeId);

    // Cleanup on unmount or recipe change
    return () => {
      if (wsManagerRef.current) {
        wsManagerRef.current.disconnect();
        wsManagerRef.current = null;
      }
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
      payload: { content: content.trim() }
    };
    
    const newMessages = [...messagesRef.current, userMessage];
    messagesRef.current = newMessages;
    setMessages(newMessages);

    // Send via WebSocket
    try {
      wsManagerRef.current.sendChatMessage(content.trim());
    } catch (error) {
      setError('Not connected. Please wait...');
    }
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