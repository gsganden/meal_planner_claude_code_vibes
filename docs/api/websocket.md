# WebSocket API Documentation

## Overview

The Recipe Chat Assistant uses WebSocket connections for real-time recipe interaction. The WebSocket protocol implements message-based authentication with automatic re-authentication support.

## Connection Flow

### 1. Initial Connection

```
ws://localhost:8000/v1/chat/{recipe_id}
wss://your-domain.com/v1/chat/{recipe_id}
```

- Connect without authentication headers
- Connection is accepted immediately
- Client has 5 seconds to authenticate

### 2. Authentication

After connection, send an authentication message within 5 seconds:

```json
{
  "type": "auth",
  "id": "auth_123456",
  "timestamp": "2024-01-20T10:30:00.000Z",
  "payload": {
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
}
```

**Success Response:**
```json
{
  "type": "recipe_update",
  "id": "update_123",
  "timestamp": "2024-01-20T10:30:01.000Z",
  "payload": {
    "content": "Connected to recipe chat. How can I help you with this recipe?",
    "recipe_data": {
      "id": "recipe_id",
      "title": "Recipe Title",
      "ingredients": [...],
      "steps": [...]
    }
  }
}
```

**Failure:**
- Connection closed with code 1008 (Policy Violation)
- Reasons: Invalid token, expired token, timeout, wrong recipe ownership

## Message Types

### Client Messages

#### 1. Authentication Message
```json
{
  "type": "auth",
  "id": "unique_message_id",
  "timestamp": "ISO 8601 timestamp",
  "payload": {
    "token": "JWT access token"
  }
}
```

#### 2. Chat Message
```json
{
  "type": "chat_message",
  "id": "msg_123456",
  "timestamp": "2024-01-20T10:31:00.000Z",
  "payload": {
    "content": "Make this recipe vegetarian"
  }
}
```

### Server Messages

#### 1. Recipe Update
```json
{
  "type": "recipe_update",
  "id": "update_456",
  "timestamp": "2024-01-20T10:31:05.000Z",
  "payload": {
    "request_id": "msg_123456",
    "content": "I've updated your recipe to be vegetarian...",
    "recipe_data": {
      "id": "recipe_id",
      "title": "Vegetarian Recipe",
      "ingredients": [...],
      "steps": [...]
    }
  }
}
```

#### 2. Authentication Required
```json
{
  "type": "auth_required",
  "id": "auth_req_789",
  "timestamp": "2024-01-20T10:44:00.000Z",
  "payload": {
    "reason": "token_expiring"
  }
}
```

#### 3. Error Message
```json
{
  "type": "error",
  "id": "err_321",
  "timestamp": "2024-01-20T10:31:00.000Z",
  "payload": {
    "error": "invalid_message",
    "message": "Message format is invalid"
  }
}
```

## Re-Authentication Flow

1. Server monitors token expiry
2. At 14 minutes (1 minute before 15-minute expiry), server sends `auth_required`
3. Client should immediately send new `auth` message
4. Connection remains active during re-authentication
5. If re-auth fails, connection is closed

## Connection States

| State | Description |
|-------|-------------|
| `connecting` | WebSocket connection being established |
| `authenticating` | Waiting for auth message or processing auth |
| `authenticated` | Successfully authenticated and ready |
| `reconnecting` | Connection lost, attempting to reconnect |
| `error` | Fatal error occurred |
| `disconnected` | Connection closed |

## Error Codes

| Code | Reason | Description |
|------|--------|-------------|
| 1000 | Normal Closure | Client or server initiated graceful close |
| 1001 | Going Away | Server is shutting down |
| 1008 | Policy Violation | Authentication failed or timeout |
| 1011 | Internal Error | Server encountered an error |

## Client Implementation Example

### JavaScript/TypeScript

```javascript
class RecipeWebSocket {
  constructor(recipeId, token) {
    this.recipeId = recipeId;
    this.token = token;
    this.ws = null;
    this.messageQueue = [];
    this.isAuthenticated = false;
  }

  connect() {
    const wsUrl = `wss://api.example.com/v1/chat/${this.recipeId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.sendAuth();
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = (event) => {
      if (event.code === 1008) {
        console.error('Authentication failed');
      }
    };
  }

  sendAuth() {
    this.send({
      type: 'auth',
      id: `auth_${Date.now()}`,
      timestamp: new Date().toISOString(),
      payload: { token: this.token }
    });
  }

  handleMessage(message) {
    switch (message.type) {
      case 'recipe_update':
        if (!this.isAuthenticated) {
          this.isAuthenticated = true;
          this.flushMessageQueue();
        }
        this.onRecipeUpdate(message.payload);
        break;
      
      case 'auth_required':
        this.refreshTokenAndReauth();
        break;
      
      case 'error':
        this.onError(message.payload);
        break;
    }
  }

  sendChatMessage(content) {
    const message = {
      type: 'chat_message',
      id: `msg_${Date.now()}`,
      timestamp: new Date().toISOString(),
      payload: { content }
    };

    if (this.isAuthenticated) {
      this.send(message);
    } else {
      this.messageQueue.push(message);
    }
  }

  send(message) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }
}
```

### Python

```python
import asyncio
import websockets
import json
from datetime import datetime

class RecipeWebSocket:
    def __init__(self, recipe_id, token):
        self.recipe_id = recipe_id
        self.token = token
        self.authenticated = False

    async def connect(self):
        uri = f"wss://api.example.com/v1/chat/{self.recipe_id}"
        
        async with websockets.connect(uri) as websocket:
            # Send auth immediately
            await self.send_auth(websocket)
            
            # Handle messages
            async for message in websocket:
                await self.handle_message(websocket, json.loads(message))

    async def send_auth(self, websocket):
        auth_msg = {
            "type": "auth",
            "id": f"auth_{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat() + "Z",
            "payload": {"token": self.token}
        }
        await websocket.send(json.dumps(auth_msg))

    async def handle_message(self, websocket, message):
        if message["type"] == "recipe_update" and not self.authenticated:
            self.authenticated = True
            print("Authenticated successfully")
        elif message["type"] == "auth_required":
            # Refresh token and re-authenticate
            await self.send_auth(websocket)
```

## Rate Limiting

- WebSocket messages: 30 messages per minute per connection
- Connection attempts: 10 per minute per IP
- Authentication attempts: 5 per connection

## Best Practices

1. **Implement Reconnection Logic**
   - Use exponential backoff
   - Start at 1 second, max 30 seconds
   - Reset delay on successful connection

2. **Message Queueing**
   - Queue messages during authentication
   - Flush queue after successful auth
   - Clear queue on disconnect

3. **Token Management**
   - Refresh tokens proactively before expiry
   - Handle `auth_required` messages immediately
   - Store tokens securely

4. **Error Handling**
   - Parse all error messages
   - Implement appropriate user feedback
   - Log errors for debugging

5. **Connection State UI**
   - Show connection status to users
   - Indicate when authenticating
   - Disable UI during reconnection

## Testing

### Manual Testing with wscat

```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/v1/chat/recipe_id

# Send auth message
{"type":"auth","id":"auth_1","timestamp":"2024-01-20T10:00:00Z","payload":{"token":"your_jwt_token"}}

# Send chat message
{"type":"chat_message","id":"msg_1","timestamp":"2024-01-20T10:00:01Z","payload":{"content":"Make it spicy"}}
```

### Automated Testing

See the test examples in:
- `/tests/test_websocket.py` - Unit tests
- `/tests/test_websocket_integration.py` - Integration tests
- `/tests/test_websocket_spec_compliance.py` - Spec compliance tests

## Migration from Header-Based Auth

### Before (Deprecated)
```javascript
// Old way - DO NOT USE
const ws = new WebSocket(url, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

### After (Current)
```javascript
// New way - message-based auth
const ws = new WebSocket(url);
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    id: 'auth_123',
    timestamp: new Date().toISOString(),
    payload: { token }
  }));
};
```

## Security Considerations

1. **Token Transmission**
   - Tokens are sent in message payload, not headers
   - Use WSS (TLS) in production
   - Never log tokens

2. **Authentication Timeout**
   - 5-second timeout prevents connection hanging
   - Limits brute force attempts
   - Enforced server-side

3. **Recipe Ownership**
   - Server validates user owns the recipe
   - Prevents unauthorized access
   - Checked on every connection

4. **Message Validation**
   - All messages validated with Pydantic
   - Invalid messages return errors
   - Prevents injection attacks