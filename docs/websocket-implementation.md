# WebSocket Message-Based Authentication Implementation

## Overview

This document describes the WebSocket message-based authentication protocol implementation for the Recipe Chat Assistant. The implementation follows the WebSocket specification that requires authentication via message protocol rather than headers or query parameters.

## Key Features

- **5-second authentication timeout**: Clients must send an auth message within 5 seconds of connection
- **Message-based authentication**: Authentication is performed via WebSocket messages, not headers
- **Re-authentication support**: Automatic re-authentication at 14 minutes (before JWT expiry)
- **Connection state management**: Clear state tracking from disconnected to authenticated
- **Automatic reconnection**: Exponential backoff reconnection on unexpected disconnects
- **Message queueing**: Messages sent while authenticating are queued and sent after authentication

## Backend Implementation

### WebSocket Handler (`src/chat/websocket.py`)

The WebSocket handler now implements the complete message-based authentication flow:

```python
async def handle_chat(websocket: WebSocket, recipe_id: str, db: AsyncSession):
    await websocket.accept()
    
    # Wait for auth message (5 second timeout)
    try:
        auth_data = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication timeout")
        return
```

### Message Types (`src/models/schemas.py`)

All WebSocket messages follow a consistent structure:

```python
class MessageType(str, Enum):
    AUTH = "auth"
    CHAT_MESSAGE = "chat_message"
    AUTH_REQUIRED = "auth_required"
    RECIPE_UPDATE = "recipe_update"
    ERROR = "error"
```

### Token Expiry Monitoring

A background task monitors token expiry and sends `auth_required` messages:

```python
async def monitor_token_expiry(websocket: WebSocket, token_expiry: int, client_id: str):
    # Calculate time until 14 minutes (1 minute before token expires)
    current_time = datetime.utcnow().timestamp()
    time_until_warning = max(0, token_expiry - current_time - 60)
    
    if time_until_warning > 0:
        await asyncio.sleep(time_until_warning)
        
        # Send auth_required message
        auth_required = AuthRequiredMessage(
            payload={"reason": "Token expiring soon"}
        )
        await manager.send_json(websocket, json.loads(auth_required.model_dump_json()))
```

## Frontend Implementation

### WebSocket Manager (`frontend_app/src/lib/websocket.ts`)

The WebSocket manager handles all connection logic:

```typescript
export class WebSocketManager {
  private state: ConnectionState = 'disconnected';
  private messageQueue: QueuedMessage[] = [];
  
  async connect(recipeId: string) {
    this.ws = new WebSocket(`${this.wsUrl}/v1/chat/${recipeId}`);
    
    this.ws.onopen = () => {
      this.setState('authenticating');
      this.sendAuthMessage();
      this.startAuthTimeout();
    };
  }
}
```

### React Hook (`frontend_app/src/hooks/useWebSocket.ts`)

The `useWebSocket` hook provides a simple interface for React components:

```typescript
export function useWebSocket(recipeId: string): UseWebSocketReturn {
  const [state, setState] = useState<ConnectionState>('disconnected');
  const [messages, setMessages] = useState<Message[]>([]);
  
  // ... WebSocket setup and management
  
  return {
    state,
    messages,
    sendMessage,
    lastRecipeUpdate,
    error,
    reconnect
  };
}
```

### Connection States

The implementation tracks these connection states:

- `disconnected`: Not connected to WebSocket
- `connecting`: WebSocket connection in progress
- `authenticating`: Connected, waiting for auth confirmation
- `authenticated`: Fully authenticated and ready
- `reconnecting`: Attempting to reconnect after disconnect
- `error`: Connection error occurred

## Message Flow

### Initial Connection

1. Client connects to WebSocket endpoint
2. Server accepts connection
3. Client sends auth message within 5 seconds
4. Server validates token and user
5. Server sends initial recipe update
6. Connection is now authenticated

### Re-authentication Flow

1. Server monitors token expiry
2. At 14 minutes, server sends `auth_required` message
3. Client refreshes token and sends new auth message
4. Server validates new token
5. Connection continues without interruption

### Error Handling

- **Authentication timeout**: Connection closed with code 1008
- **Invalid token**: Connection closed with code 1008
- **Invalid message format**: Error message sent, connection continues
- **Processing errors**: Error message sent, connection continues

## Testing

### Backend Tests

All WebSocket tests have been updated to use message-based authentication:

```python
def test_websocket_connection_success(test_client_with_recipe):
    client, token, recipe_id = test_client_with_recipe
    
    with client.websocket_connect(f"/v1/chat/{recipe_id}") as websocket:
        # Send auth message
        websocket.send_json({
            "type": "auth",
            "payload": {"token": token}
        })
        
        # Should receive initial recipe update
        data = websocket.receive_json()
        assert data["type"] == "recipe_update"
```

### Frontend Testing

The WebSocket manager can be tested with mocked WebSocket connections:

```typescript
describe('WebSocketManager', () => {
  it('sends auth message on connect', async () => {
    const mockWs = new MockWebSocket();
    const manager = new WebSocketManager();
    
    await manager.connect('recipe-123');
    
    expect(mockWs.sentMessages[0]).toMatchObject({
      type: 'auth',
      payload: { token: 'mock-token' }
    });
  });
});
```

## Migration Notes

This implementation is a breaking change from header-based authentication. Key differences:

1. **No more headers/query params**: Authentication is only via messages
2. **5-second timeout**: Clients must authenticate quickly
3. **Structured messages**: All messages follow the defined schema
4. **State management**: Clients must track connection state

## Security Considerations

- Tokens are never exposed in URLs or headers
- 5-second timeout prevents connection hijacking
- Automatic re-authentication prevents token expiry issues
- Proper WebSocket close codes indicate auth failures

## Example Usage

### React Component

```jsx
import { RecipeChat } from '@/components/RecipeChat';

function RecipeEditor({ recipeId }) {
  return (
    <RecipeChat 
      recipeId={recipeId}
      onRecipeUpdate={(data) => console.log('Recipe updated:', data)}
    />
  );
}
```

### Direct WebSocket Usage

```typescript
const wsManager = new WebSocketManager('wss://api.example.com');

wsManager.on('state', (state) => {
  console.log('Connection state:', state);
});

wsManager.on('message', (message) => {
  console.log('Received:', message);
});

await wsManager.connect('recipe-123');
wsManager.sendChatMessage('Make this recipe vegetarian');
```