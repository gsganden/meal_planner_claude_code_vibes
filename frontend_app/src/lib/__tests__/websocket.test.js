import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WebSocketManager } from '../websocket';

// Mock auth module
vi.mock('../auth', () => ({
  getAccessToken: vi.fn(() => 'mock-token'),
  refreshAccessToken: vi.fn(() => Promise.resolve('new-mock-token'))
}));

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    this.onopen = null;
    this.onclose = null;
    this.onmessage = null;
    this.onerror = null;
    this.sentMessages = [];
    
    // Store instance for access in tests
    MockWebSocket.lastInstance = this;
    
    // Simulate connection after a tick
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) this.onopen();
    }, 0);
  }

  send(data) {
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({ code: 1000, reason: 'Normal closure' });
    }
  }
}

// Replace global WebSocket with mock
global.WebSocket = MockWebSocket;

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn((key) => {
    if (key === 'access_token') return 'mock-token';
    if (key === 'refresh_token') return 'mock-refresh-token';
    return null;
  }),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
};
global.localStorage = localStorageMock;

describe('WebSocketManager', () => {
  let manager;
  let mockWebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    manager = new WebSocketManager('ws://test.com');
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    if (manager) {
      manager.disconnect();
    }
  });

  describe('Connection Management', () => {
    it('should create WebSocket connection', async () => {
      const stateHandler = vi.fn();
      manager.on('state', stateHandler);

      manager.connect('recipe-123');
      
      // Should be connecting
      expect(stateHandler).toHaveBeenCalledWith('connecting');
      
      // Wait for WebSocket to open
      await vi.advanceTimersByTimeAsync(10);
      
      // Should be authenticating after open
      expect(stateHandler).toHaveBeenCalledWith('authenticating');
      
      // Check auth message was sent
      expect(manager.ws).toBeDefined();
      expect(manager.ws.sentMessages).toBeDefined();
      expect(manager.ws.sentMessages).toHaveLength(1);
      const authMsg = JSON.parse(manager.ws.sentMessages[0]);
      expect(authMsg.type).toBe('auth');
      expect(authMsg.payload.token).toBe('mock-token');
    });

    it('should handle authentication timeout', async () => {
      const stateHandler = vi.fn();
      manager.on('state', stateHandler);

      manager.connect('recipe-123');
      await vi.runAllTimersAsync();

      // Advance time to trigger auth timeout (5 seconds)
      vi.advanceTimersByTime(5000);

      expect(stateHandler).toHaveBeenCalledWith('error');
    });

    it('should handle successful authentication', async () => {
      const stateHandler = vi.fn();
      manager.on('state', stateHandler);

      manager.connect('recipe-123');
      
      // Wait for WebSocket to open
      await vi.advanceTimersByTimeAsync(10);
      
      // Simulate auth success message before timeout
      manager.ws.onmessage({
        data: JSON.stringify({
          type: 'recipe_update',
          id: 'msg_1',
          timestamp: new Date().toISOString(),
          payload: { content: 'Connected' }
        })
      });

      expect(stateHandler).toHaveBeenCalledWith('authenticated');
    });

    it('should reconnect with exponential backoff', async () => {
      manager.connect('recipe-123');
      await vi.advanceTimersByTimeAsync(10);

      // Get the WebSocket instance
      const ws = MockWebSocket.lastInstance;
      expect(ws).toBeDefined();
      
      // Simulate unexpected close
      ws.onclose({ code: 1006, reason: 'Abnormal closure' });

      // Should schedule reconnect
      expect(manager.reconnectTimeout).toBeDefined();

      // First reconnect after 1 second
      vi.advanceTimersByTime(1000);
      
      // Should create new connection
      expect(manager.getState()).toBe('connecting');
    });

    it('should not reconnect on normal close', async () => {
      manager.connect('recipe-123');
      await vi.advanceTimersByTimeAsync(10);

      // Normal disconnect
      manager.disconnect();

      // Should not schedule reconnect
      expect(manager.reconnectTimeout).toBeNull();
    });
  });

  describe('Message Handling', () => {
    beforeEach(async () => {
      manager.connect('recipe-123');
      await vi.advanceTimersByTimeAsync(10);
      
      // Get the WebSocket instance
      const ws = MockWebSocket.lastInstance;
      expect(ws).toBeDefined();
      
      // Simulate successful auth
      ws.onmessage({
        data: JSON.stringify({
          type: 'recipe_update',
          id: 'auth_response',
          timestamp: new Date().toISOString(),
          payload: { content: 'Connected' }
        })
      });
    });

    it('should send chat messages when authenticated', () => {
      manager.sendChatMessage('Hello world');

      // Should have auth message + chat message
      expect(manager.ws.sentMessages).toHaveLength(2);
      const chatMsg = JSON.parse(manager.ws.sentMessages[1]);
      expect(chatMsg.type).toBe('chat_message');
      expect(chatMsg.payload.content).toBe('Hello world');
    });

    it('should queue messages during authentication', async () => {
      // Create new manager
      const newManager = new WebSocketManager('ws://test.com');
      newManager.connect('recipe-123');
      
      // Wait for WebSocket to open
      await vi.advanceTimersByTimeAsync(10);
      
      // Send message during authentication (before auth completes)
      newManager.sendChatMessage('Queued message');
      
      // Get the WebSocket instance
      const ws = MockWebSocket.lastInstance;
      expect(ws).toBeDefined();

      // Simulate auth success
      ws.onmessage({
        data: JSON.stringify({
          type: 'recipe_update',
          id: 'auth_response',
          timestamp: new Date().toISOString(),
          payload: { content: 'Connected' }
        })
      });

      // Should send queued message (auth message + queued message)
      expect(ws.sentMessages).toHaveLength(2);
      const queuedMsg = JSON.parse(ws.sentMessages[1]);
      expect(queuedMsg.payload.content).toBe('Queued message');
      
      newManager.disconnect();
    });

    it('should handle re-authentication message', () => {
      const stateHandler = vi.fn();
      manager.on('state', stateHandler);

      // Receive auth_required message
      manager.ws.onmessage({
        data: JSON.stringify({
          type: 'auth_required',
          id: 'reauth_1',
          timestamp: new Date().toISOString(),
          payload: { reason: 'token_expiring' }
        })
      });

      // Should send new auth message
      const lastMsg = JSON.parse(manager.ws.sentMessages[manager.ws.sentMessages.length - 1]);
      expect(lastMsg.type).toBe('auth');
    });

    it('should emit message events', () => {
      const messageHandler = vi.fn();
      manager.on('message', messageHandler);

      const testMessage = {
        type: 'recipe_update',
        id: 'update_1',
        timestamp: new Date().toISOString(),
        payload: { content: 'Recipe updated' }
      };

      manager.ws.onmessage({ data: JSON.stringify(testMessage) });

      expect(messageHandler).toHaveBeenCalledWith(testMessage);
    });
  });

  describe('Error Handling', () => {
    it('should handle WebSocket errors', async () => {
      const stateHandler = vi.fn();
      manager.on('state', stateHandler);

      manager.connect('recipe-123');
      await vi.advanceTimersByTimeAsync(10);

      // Get the WebSocket instance
      const ws = MockWebSocket.lastInstance;
      expect(ws).toBeDefined();
      
      // Simulate error
      ws.onerror(new Error('Connection failed'));

      expect(stateHandler).toHaveBeenCalledWith('error');
    });

    it('should handle invalid JSON messages', async () => {
      manager.connect('recipe-123');
      await vi.advanceTimersByTimeAsync(10);

      // Get the WebSocket instance
      const ws = MockWebSocket.lastInstance;
      expect(ws).toBeDefined();
      
      // Should not throw
      expect(() => {
        ws.onmessage({ data: 'invalid json' });
      }).not.toThrow();
    });

    it('should handle missing auth token', () => {
      // Remove token from localStorage
      const originalGetItem = localStorage.getItem;
      localStorage.getItem = vi.fn(() => null);

      const newManager = new WebSocketManager('ws://test.com');
      
      expect(() => {
        newManager.connect('recipe-123');
      }).toThrow('No authentication token');

      localStorage.getItem = originalGetItem;
    });
  });

  describe('State Management', () => {
    it('should track connection state accurately', async () => {
      expect(manager.getState()).toBe('disconnected');
      
      manager.connect('recipe-123');
      expect(manager.getState()).toBe('connecting');
      
      await vi.advanceTimersByTimeAsync(10);
      expect(manager.getState()).toBe('authenticating');
      
      // Get the WebSocket instance
      const ws = MockWebSocket.lastInstance;
      expect(ws).toBeDefined();
      
      // Simulate auth success
      ws.onmessage({
        data: JSON.stringify({
          type: 'recipe_update',
          id: 'auth_response',
          timestamp: new Date().toISOString(),
          payload: { content: 'Connected' }
        })
      });
      
      expect(manager.getState()).toBe('authenticated');
      expect(manager.isConnected()).toBe(true);
    });

    it('should prevent duplicate connections', async () => {
      manager.connect('recipe-123');
      await vi.advanceTimersByTimeAsync(10);

      const firstWs = manager.ws;
      
      // Try to connect again
      manager.connect('recipe-456');
      
      // Should close first connection
      expect(firstWs.readyState).toBe(WebSocket.CLOSED);
    });
  });

  describe('Event Management', () => {
    it('should add and remove event listeners', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      manager.on('state', handler1);
      manager.on('state', handler2);

      manager.emit('state', 'connecting');

      expect(handler1).toHaveBeenCalledWith('connecting');
      expect(handler2).toHaveBeenCalledWith('connecting');

      manager.off('state', handler1);
      manager.emit('state', 'authenticated');

      expect(handler1).toHaveBeenCalledTimes(1);
      expect(handler2).toHaveBeenCalledTimes(2);
    });

    it('should handle removing non-existent listeners', () => {
      const handler = vi.fn();
      
      // Should not throw
      expect(() => {
        manager.off('state', handler);
      }).not.toThrow();
    });
  });
});