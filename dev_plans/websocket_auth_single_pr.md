# WebSocket Auth Message Protocol - Single PR Implementation

## Context: Pre-Production Advantage
Since we're pre-production, we can make breaking changes without migration complexity. This is the perfect time to implement the correct protocol.

## PR Title
`feat: Implement WebSocket message-based authentication with re-auth support`

## PR Scope (All or Nothing! 🚀)

### Backend Changes

#### 1. Update WebSocket Handler (`src/chat/websocket.py`)
```python
async def handle_chat(websocket: WebSocket, recipe_id: str, db: AsyncSession):
    await websocket.accept()
    
    # Wait for auth message (5 second timeout)
    try:
        auth_msg = await asyncio.wait_for(
            websocket.receive_json(), 
            timeout=5.0
        )
        
        if auth_msg.get("type") != "auth":
            await websocket.close(code=1008, reason="First message must be auth")
            return
            
        token = auth_msg.get("payload", {}).get("token")
        if not token:
            await websocket.close(code=1008, reason="Missing auth token")
            return
            
        user = await get_user_from_token(token, db)
        if not user:
            await websocket.close(code=1008, reason="Invalid token")
            return
            
    except asyncio.TimeoutError:
        await websocket.close(code=1008, reason="Authentication timeout")
        return
    
    # Set up re-auth timer
    asyncio.create_task(monitor_token_expiry(websocket, token))
    
    # ... rest of connection handling
```

#### 2. Add Message Types (`src/models/schemas.py`)
```python
class MessageType(str, Enum):
    AUTH = "auth"
    CHAT_MESSAGE = "chat_message"
    AUTH_REQUIRED = "auth_required"
    RECIPE_UPDATE = "recipe_update"
    ERROR = "error"

class AuthMessage(BaseModel):
    type: Literal["auth"]
    id: str
    timestamp: datetime
    payload: dict[str, str]  # {token: "..."}

class ChatMessage(BaseModel):
    type: Literal["chat_message"]
    id: str
    timestamp: datetime
    payload: dict[str, str]  # {content: "..."}
```

#### 3. Implement Re-authentication Monitor
```python
async def monitor_token_expiry(websocket: WebSocket, token: str):
    # Wait until 14 minutes
    await asyncio.sleep(14 * 60)
    
    # Send auth_required message
    await websocket.send_json({
        "type": "auth_required",
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {"reason": "Token expiring soon"}
    })
    
    # Wait for new auth message (30 seconds)
    try:
        reauth_msg = await asyncio.wait_for(
            wait_for_auth_message(websocket),
            timeout=30.0
        )
        # Validate new token and continue
    except asyncio.TimeoutError:
        await websocket.close(code=1008, reason="Re-authentication timeout")
```

### Frontend Changes

#### 1. New WebSocket Manager (`frontend_app/src/lib/websocket.ts`)
```typescript
export class WebSocketManager {
  private ws: WebSocket | null = null;
  private state: ConnectionState = 'disconnected';
  private authTimer: NodeJS.Timeout | null = null;
  private messageQueue: QueuedMessage[] = [];
  
  async connect(recipeId: string) {
    this.state = 'connecting';
    this.ws = new WebSocket(`${WS_URL}/v1/chat/${recipeId}`);
    
    this.ws.onopen = () => {
      this.state = 'authenticating';
      this.sendAuth();
      
      // Start 5-second timeout
      this.authTimer = setTimeout(() => {
        this.handleAuthTimeout();
      }, 5000);
    };
    
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      
      switch (msg.type) {
        case 'recipe_update':
          if (this.state === 'authenticating') {
            this.onAuthenticated();
          }
          this.handleRecipeUpdate(msg);
          break;
          
        case 'auth_required':
          this.handleReauth();
          break;
          
        case 'error':
          this.handleError(msg);
          break;
      }
    };
  }
  
  private sendAuth() {
    const token = getAccessToken();
    this.send({
      type: 'auth',
      id: generateId(),
      timestamp: new Date().toISOString(),
      payload: { token }
    });
  }
  
  private async handleReauth() {
    try {
      const newToken = await refreshToken();
      localStorage.setItem('access_token', newToken);
      this.sendAuth();
    } catch (error) {
      this.disconnect('Failed to refresh authentication');
    }
  }
}
```

#### 2. Update React Components
```typescript
// src/components/RecipeChat.tsx
export function RecipeChat({ recipeId }: Props) {
  const { state, messages, sendMessage } = useWebSocket(recipeId);
  
  return (
    <div className="recipe-chat">
      <ConnectionStatus state={state} />
      
      <MessageList messages={messages} />
      
      <MessageInput 
        onSend={sendMessage}
        disabled={state !== 'authenticated'}
        placeholder={
          state === 'authenticating' 
            ? 'Authenticating...' 
            : 'Type a message...'
        }
      />
    </div>
  );
}

// src/components/ConnectionStatus.tsx
export function ConnectionStatus({ state }: { state: ConnectionState }) {
  const statusConfig = {
    disconnected: { color: 'red', text: 'Disconnected' },
    connecting: { color: 'yellow', text: 'Connecting...' },
    authenticating: { color: 'yellow', text: 'Authenticating...' },
    authenticated: { color: 'green', text: 'Connected' },
    reconnecting: { color: 'yellow', text: 'Reconnecting...' },
  };
  
  const config = statusConfig[state];
  
  return (
    <div className={`connection-status ${config.color}`}>
      <span className="status-dot" />
      {config.text}
    </div>
  );
}
```

### Test Updates

#### Backend Tests
```python
async def test_websocket_auth_timeout():
    """Test 5-second auth timeout"""
    async with client.websocket_connect(f"/v1/chat/{recipe_id}") as ws:
        # Don't send auth message
        await asyncio.sleep(6)
        
        # Should receive close frame
        with pytest.raises(WebSocketDisconnect) as exc:
            await ws.receive_json()
        assert exc.value.code == 1008

async def test_websocket_auth_message_required():
    """Test first message must be auth"""
    async with client.websocket_connect(f"/v1/chat/{recipe_id}") as ws:
        # Send non-auth message first
        await ws.send_json({"type": "chat_message", "payload": {"content": "hi"}})
        
        with pytest.raises(WebSocketDisconnect) as exc:
            await ws.receive_json()
        assert exc.value.code == 1008

async def test_websocket_reauth_flow():
    """Test re-authentication at 14 minutes"""
    # ... test implementation
```

#### Frontend Tests
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
  
  it('handles auth timeout', async () => {
    jest.useFakeTimers();
    const manager = new WebSocketManager();
    
    await manager.connect('recipe-123');
    jest.advanceTimersByTime(5001);
    
    expect(manager.state).toBe('disconnected');
  });
});
```

## Implementation Checklist

### Hour 1-4: Backend Core
- [ ] Remove header/query auth from websocket.py
- [ ] Add auth message handling with timeout
- [ ] Create message type schemas
- [ ] Update connection flow

### Hour 5-8: Backend Re-auth
- [ ] Add token expiry monitoring
- [ ] Implement auth_required message
- [ ] Handle re-authentication flow
- [ ] Add comprehensive logging

### Hour 9-12: Backend Tests
- [ ] Update ALL WebSocket tests
- [ ] Add timeout tests
- [ ] Add re-auth tests
- [ ] Test error scenarios

### Hour 13-16: Frontend Core
- [ ] Create WebSocketManager class
- [ ] Implement auth message sending
- [ ] Add connection state management
- [ ] Handle message queuing

### Hour 17-20: Frontend UI
- [ ] Add connection status component
- [ ] Update chat UI for auth states
- [ ] Implement error handling
- [ ] Add loading states

### Hour 21-24: Frontend Tests
- [ ] Unit test WebSocketManager
- [ ] Test React components
- [ ] Mock WebSocket for testing
- [ ] Integration tests

### Hour 25-28: Integration & Polish
- [ ] Full end-to-end testing
- [ ] Update API documentation
- [ ] Add debug logging
- [ ] Performance testing

### Hour 29: Buffer
- [ ] Fix any issues found
- [ ] Final testing pass
- [ ] Update README

## Why This Works as a Single PR in Pre-Production

1. **No Migration Needed**: No existing users to break
2. **Clean Implementation**: Do it right the first time
3. **Faster Development**: No compatibility layers
4. **Better Testing**: Test the actual implementation, not transitions
5. **Simpler Code**: No feature flags or dual modes

## Testing Strategy

1. **Unit Tests**: Every new function/class
2. **Integration Tests**: Full auth flow
3. **E2E Tests**: Real browser to real backend
4. **Load Tests**: 100+ concurrent connections
5. **Chaos Tests**: Network failures, timeouts

## PR Description Template

```markdown
## Summary
Implements WebSocket authentication via message protocol as specified in RFC-XXX.

## Changes
- WebSocket connections now require auth message within 5 seconds
- Automatic re-authentication at 14 minutes
- Comprehensive connection state management
- Full test coverage for all scenarios

## Breaking Changes
- WebSocket clients must send auth message after connection
- Header/query authentication no longer supported

## Testing
- [ ] All backend tests passing
- [ ] All frontend tests passing  
- [ ] Manual testing completed
- [ ] Load testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No console.logs or debug code

Fixes #XXX
```

## Go Time! 🚀

This is the perfect opportunity to implement the protocol correctly without technical debt. Since we're pre-production:

1. No backwards compatibility needed
2. Can break things without user impact
3. One PR keeps the implementation cohesive
4. Faster to implement without migration code

The key is thorough testing - with no users to catch bugs, our tests must be comprehensive!