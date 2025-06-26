export class WebSocketManager {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.state = 'disconnected';
    this.recipeId = null;
    this.messageQueue = [];
    this.authTimeout = null;
    this.reAuthTimeout = null;
    this.reconnectTimeout = null;
    this.reconnectDelay = 1000; // Start with 1 second
    this.maxReconnectDelay = 30000; // Max 30 seconds
    this.tokenExpiryMonitor = null;
    this.listeners = {
      state: [],
      message: [],
      error: []
    };
  }

  connect(recipeId) {
    if (this.ws && this.state !== 'disconnected') {
      console.warn('WebSocket already connected');
      this.disconnect();
    }

    this.recipeId = recipeId;
    this.setState('connecting');

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No authentication token');
      }

      this.ws = new WebSocket(`${this.wsUrl}/v1/chat/${recipeId}`);
      
      this.ws.onopen = () => this.handleOpen();
      this.ws.onclose = (event) => this.handleClose(event);
      this.ws.onerror = (error) => this.handleError(error);
      this.ws.onmessage = (event) => this.handleMessage(event);
    } catch (error) {
      this.setState('error');
      this.emit('error', error);
      throw error;
    }
  }

  disconnect() {
    this.clearTimeouts();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.setState('disconnected');
    this.messageQueue = [];
  }

  handleOpen() {
    this.setState('authenticating');
    this.sendAuthMessage();
    this.startAuthTimeout();
  }

  handleClose(event) {
    this.clearTimeouts();
    
    if (event.code === 1008) {
      // Policy violation (auth failed)
      this.setState('error');
      this.emit('error', new Error('Authentication failed'));
    } else if (event.code !== 1000 && this.state !== 'disconnected') {
      // Unexpected close, attempt reconnect
      this.scheduleReconnect();
    } else {
      this.setState('disconnected');
    }
  }

  handleError(error) {
    console.error('WebSocket error:', error);
    this.setState('error');
    this.emit('error', error);
  }

  handleMessage(event) {
    try {
      const message = JSON.parse(event.data);
      
      // Handle auth success (first recipe_update after auth)
      if (this.state === 'authenticating' && message.type === 'recipe_update') {
        this.handleAuthSuccess();
      }
      
      // Handle re-authentication request
      if (message.type === 'auth_required') {
        this.handleReAuthRequired();
        return; // Don't emit this message to listeners
      }
      
      // Emit message to listeners
      this.emit('message', message);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  sendAuthMessage() {
    const token = localStorage.getItem('access_token');
    if (!token) {
      this.disconnect();
      throw new Error('No authentication token');
    }

    const authMessage = {
      type: 'auth',
      id: `auth_${Date.now()}`,
      timestamp: new Date().toISOString(),
      payload: { token }
    };

    this.send(authMessage);
  }

  handleAuthSuccess() {
    this.clearAuthTimeout();
    this.setState('authenticated');
    this.processMessageQueue();
    this.startTokenExpiryMonitor();
    this.reconnectDelay = 1000; // Reset reconnect delay on success
  }

  handleReAuthRequired() {
    this.setState('authenticating');
    
    // Try to refresh token first
    refreshAccessToken()
      .then(() => {
        this.sendAuthMessage();
        this.startAuthTimeout();
      })
      .catch(() => {
        // If refresh fails, disconnect
        this.disconnect();
        this.emit('error', new Error('Session expired'));
      });
  }

  startAuthTimeout() {
    this.authTimeout = setTimeout(() => {
      console.error('Authentication timeout');
      this.disconnect();
      this.setState('error');
    }, 5000);
  }

  clearAuthTimeout() {
    if (this.authTimeout) {
      clearTimeout(this.authTimeout);
      this.authTimeout = null;
    }
  }

  startTokenExpiryMonitor() {
    // Monitor token expiry and request re-auth at 14 minutes
    this.tokenExpiryMonitor = setTimeout(() => {
      // This would be triggered by the server sending auth_required
      // But we can proactively prepare for it
      console.log('Token expiry approaching...');
    }, 14 * 60 * 1000); // 14 minutes
  }

  clearTimeouts() {
    this.clearAuthTimeout();
    
    if (this.reAuthTimeout) {
      clearTimeout(this.reAuthTimeout);
      this.reAuthTimeout = null;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.tokenExpiryMonitor) {
      clearTimeout(this.tokenExpiryMonitor);
      this.tokenExpiryMonitor = null;
    }
  }

  scheduleReconnect() {
    if (this.reconnectTimeout) return;
    
    this.setState('reconnecting');
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      if (this.recipeId) {
        this.connect(this.recipeId);
      }
    }, this.reconnectDelay);
    
    // Exponential backoff
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      throw new Error('WebSocket is not connected');
    }
  }

  sendChatMessage(content) {
    const message = {
      type: 'chat_message',
      id: `msg_${Date.now()}`,
      timestamp: new Date().toISOString(),
      payload: { content }
    };

    if (this.state === 'authenticated') {
      this.send(message);
    } else if (this.state === 'authenticating' || this.state === 'connecting') {
      // Queue message
      this.messageQueue.push(message);
    } else {
      throw new Error('Not connected');
    }
  }

  processMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      try {
        this.send(message);
      } catch (error) {
        console.error('Failed to send queued message:', error);
      }
    }
  }

  setState(newState) {
    if (this.state !== newState) {
      this.state = newState;
      this.emit('state', newState);
    }
  }

  getState() {
    return this.state;
  }

  isConnected() {
    return this.state === 'authenticated';
  }

  // Event emitter methods
  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in ${event} listener:`, error);
        }
      });
    }
  }
}

// Re-export the auth functions that might be used
export { getAccessToken, refreshAccessToken } from './auth';