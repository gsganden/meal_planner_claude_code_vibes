import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useWebSocket } from '../useWebSocket';
import { WebSocketManager } from '../../lib/websocket';

// Mock WebSocketManager
vi.mock('../../lib/websocket', () => {
  const mockManager = {
    connect: vi.fn(),
    disconnect: vi.fn(),
    sendChatMessage: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    getState: vi.fn(() => 'disconnected'),
    isConnected: vi.fn(() => false),
  };

  return {
    WebSocketManager: vi.fn(() => mockManager),
    ConnectionState: {
      DISCONNECTED: 'disconnected',
      CONNECTING: 'connecting',
      AUTHENTICATING: 'authenticating',
      AUTHENTICATED: 'authenticated',
      RECONNECTING: 'reconnecting',
      ERROR: 'error'
    }
  };
});

describe('useWebSocket', () => {
  let mockManager: any;
  let stateHandlers: ((state: string) => void)[] = [];
  let messageHandlers: ((message: any) => void)[] = [];

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();
    stateHandlers = [];
    messageHandlers = [];

    // Get mock manager instance
    mockManager = new (WebSocketManager as any)();
    
    // Setup event handler mocks
    mockManager.on.mockImplementation((event: string, handler: Function) => {
      if (event === 'state') {
        stateHandlers.push(handler as any);
      } else if (event === 'message') {
        messageHandlers.push(handler as any);
      }
    });

    mockManager.off.mockImplementation((event: string, handler: Function) => {
      if (event === 'state') {
        stateHandlers = stateHandlers.filter(h => h !== handler);
      } else if (event === 'message') {
        messageHandlers = messageHandlers.filter(h => h !== handler);
      }
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Connection Management', () => {
    it('should connect to WebSocket when recipe ID is provided', async () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      await waitFor(() => {
        expect(mockManager.connect).toHaveBeenCalledWith('recipe-123');
      });

      expect(result.current.state).toBe('disconnected');
    });

    it('should not connect when recipe ID is empty', () => {
      renderHook(() => useWebSocket(''));

      expect(mockManager.connect).not.toHaveBeenCalled();
    });

    it('should disconnect and cleanup on unmount', () => {
      const { unmount } = renderHook(() => useWebSocket('recipe-123'));

      unmount();

      expect(mockManager.disconnect).toHaveBeenCalled();
    });

    it('should reconnect when recipe ID changes', async () => {
      const { rerender } = renderHook(
        ({ recipeId }) => useWebSocket(recipeId),
        { initialProps: { recipeId: 'recipe-123' } }
      );

      await waitFor(() => {
        expect(mockManager.connect).toHaveBeenCalledWith('recipe-123');
      });

      // Change recipe ID
      rerender({ recipeId: 'recipe-456' });

      await waitFor(() => {
        expect(mockManager.disconnect).toHaveBeenCalled();
        expect(mockManager.connect).toHaveBeenCalledWith('recipe-456');
      });
    });
  });

  describe('State Management', () => {
    it('should update state when WebSocket state changes', async () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      // Simulate state changes
      act(() => {
        stateHandlers.forEach(handler => handler('connecting'));
      });

      expect(result.current.state).toBe('connecting');

      act(() => {
        stateHandlers.forEach(handler => handler('authenticated'));
      });

      expect(result.current.state).toBe('authenticated');
    });

    it('should set error when state is error', () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      act(() => {
        stateHandlers.forEach(handler => handler('error'));
      });

      expect(result.current.state).toBe('error');
      expect(result.current.error).toBe('Connection error. Please try again.');
    });

    it('should clear error when authenticated', () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      // Set error first
      act(() => {
        stateHandlers.forEach(handler => handler('error'));
      });

      expect(result.current.error).toBeTruthy();

      // Then authenticate
      act(() => {
        stateHandlers.forEach(handler => handler('authenticated'));
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('Message Handling', () => {
    it('should add messages to history', () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      const message1 = {
        type: 'chat_message',
        id: 'msg_1',
        timestamp: new Date().toISOString(),
        payload: { content: 'Hello' }
      };

      act(() => {
        messageHandlers.forEach(handler => handler(message1));
      });

      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0]).toEqual(message1);
    });

    it('should track last recipe update', () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      const recipeUpdate = {
        type: 'recipe_update',
        id: 'update_1',
        timestamp: new Date().toISOString(),
        payload: {
          content: 'Recipe updated',
          recipe_data: { title: 'New Recipe' }
        }
      };

      act(() => {
        messageHandlers.forEach(handler => handler(recipeUpdate));
      });

      expect(result.current.lastRecipeUpdate).toEqual(recipeUpdate);
    });

    it('should handle error messages', () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      const errorMessage = {
        type: 'error',
        id: 'err_1',
        timestamp: new Date().toISOString(),
        payload: {
          error: 'processing_error',
          message: 'Failed to process'
        }
      };

      act(() => {
        messageHandlers.forEach(handler => handler(errorMessage));
      });

      expect(result.current.error).toBe('Failed to process');
    });
  });

  describe('Sending Messages', () => {
    it('should send message when connected', () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      act(() => {
        result.current.sendMessage('Hello world');
      });

      expect(mockManager.sendChatMessage).toHaveBeenCalledWith('Hello world');
    });

    it('should show error when sending without connection', () => {
      mockManager.sendChatMessage.mockImplementationOnce(() => {
        throw new Error('Not connected');
      });

      const { result } = renderHook(() => useWebSocket('recipe-123'));

      act(() => {
        result.current.sendMessage('Hello');
      });

      expect(result.current.error).toBe('Not connected. Please wait...');
    });

    it('should add user message to history optimistically', () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      act(() => {
        result.current.sendMessage('Test message');
      });

      // Should add message immediately
      const userMessage = result.current.messages.find(
        msg => msg.type === 'chat_message' && msg.payload.content === 'Test message'
      );
      expect(userMessage).toBeDefined();
    });

    it('should trim whitespace from messages', () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      act(() => {
        result.current.sendMessage('  Trimmed message  ');
      });

      expect(mockManager.sendChatMessage).toHaveBeenCalledWith('Trimmed message');
      
      // Also check that it's stored trimmed
      const userMessage = result.current.messages.find(
        msg => msg.payload.content === 'Trimmed message'
      );
      expect(userMessage).toBeDefined();
    });
  });

  describe('Reconnection', () => {
    it('should provide reconnect function', async () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      await waitFor(() => {
        expect(mockManager.connect).toHaveBeenCalledTimes(1);
      });

      act(() => {
        result.current.reconnect();
      });

      expect(mockManager.disconnect).toHaveBeenCalled();
      expect(mockManager.connect).toHaveBeenCalledTimes(2);
    });

    it('should not reconnect without recipe ID', () => {
      const { result } = renderHook(() => useWebSocket(''));

      act(() => {
        result.current.reconnect();
      });

      expect(mockManager.connect).not.toHaveBeenCalled();
    });
  });

  describe('Message History', () => {
    it('should maintain message order', () => {
      const { result } = renderHook(() => useWebSocket('recipe-123'));

      const messages = [
        {
          type: 'chat_message',
          id: 'msg_1',
          timestamp: '2023-01-01T10:00:00Z',
          payload: { content: 'First' }
        },
        {
          type: 'recipe_update',
          id: 'update_1',
          timestamp: '2023-01-01T10:00:01Z',
          payload: { content: 'Response', recipe_data: null }
        },
        {
          type: 'chat_message',
          id: 'msg_2',
          timestamp: '2023-01-01T10:00:02Z',
          payload: { content: 'Second' }
        }
      ];

      messages.forEach(msg => {
        act(() => {
          messageHandlers.forEach(handler => handler(msg));
        });
      });

      expect(result.current.messages).toHaveLength(3);
      expect(result.current.messages[0].id).toBe('msg_1');
      expect(result.current.messages[1].id).toBe('update_1');
      expect(result.current.messages[2].id).toBe('msg_2');
    });

    it('should clear messages on disconnect', () => {
      const { result, unmount } = renderHook(() => useWebSocket('recipe-123'));

      // Add some messages
      act(() => {
        messageHandlers.forEach(handler => handler({
          type: 'chat_message',
          id: 'msg_1',
          timestamp: new Date().toISOString(),
          payload: { content: 'Test' }
        }));
      });

      expect(result.current.messages).toHaveLength(1);

      // Unmount should clear messages
      unmount();

      // Remount
      const { result: newResult } = renderHook(() => useWebSocket('recipe-123'));
      expect(newResult.current.messages).toHaveLength(0);
    });
  });

  describe('Error Handling', () => {
    it('should handle WebSocket manager creation failure', () => {
      // Mock WebSocketManager constructor to throw
      const originalWebSocketManager = WebSocketManager;
      (WebSocketManager as any).mockImplementation(() => {
        throw new Error('Failed to create WebSocket');
      });

      // Should not crash the hook
      const { result } = renderHook(() => useWebSocket('recipe-123'));
      expect(result.current.state).toBe('disconnected');

      // Restore mock
      (WebSocketManager as any).mockImplementation(() => mockManager);
    });
  });
});