# WebSocket Authentication Message Implementation Plan

## Overview
Implement WebSocket authentication via message-based protocol as specified in `websocket-chat-protocol.md`, replacing the current header/query parameter authentication.

## Current State
- Authentication happens via Authorization header or query parameter
- Connection is immediately accepted or rejected based on token presence
- No timeout mechanism for authentication
- No support for re-authentication messages

## Target State
- Client connects without authentication
- Client must send `auth` message within 5 seconds
- Server validates token from auth message
- Support for re-authentication via `auth_required` messages

## Implementation Checklist

### Phase 1: Core Authentication Message Protocol
- [x] Update `src/chat/websocket.py` to accept connections without initial auth
- [x] Add connection state tracking (Connecting, Authenticating, Connected)
- [x] Implement 5-second authentication timeout using `asyncio.wait_for`
- [x] Add message type validation for first message must be `auth` type
- [x] Parse JWT token from auth message payload instead of headers
- [x] Close connection with code 1008 if auth fails or times out

### Phase 2: Message Format Support
- [x] Define message type enums in `src/models/schemas.py`:
  - `auth`, `chat_message`, `auth_required`, `recipe_update`, `error`
- [x] Create Pydantic models for client messages:
  - `AuthMessage` with token field
  - `ChatMessage` with content field
- [x] Update message parsing to use discriminated unions
- [x] Add message ID and timestamp fields to all messages

### Phase 3: Re-authentication Flow (14-minute check)
- [x] Track connection start time and token expiry per WebSocket
- [x] Implement background task to check token expiry at 14 minutes
- [x] Send `auth_required` message when token near expiry
- [x] Handle new auth message without disconnecting
- [x] Update connection auth state after successful re-auth
- [x] Close connection if re-auth fails or times out

### Phase 4: Update Tests
- [x] Update all WebSocket tests to use message-based auth:
  - `test_websocket_authentication` - send auth message after connect
  - `test_websocket_connection_success` - verify auth flow
  - `test_websocket_chat_message` - ensure auth before chat
- [x] Add new tests:
  - [x] Test 5-second authentication timeout
  - [x] Test invalid auth message format
  - [x] Test non-auth first message rejection
  - [ ] Test re-authentication flow at 14 minutes
  - [ ] Test re-auth timeout and failure

### Phase 5: Frontend Implementation

#### WebSocket Client Updates
- [x] Create WebSocket connection state manager:
  - `connecting`, `authenticating`, `authenticated`, `reconnecting`, `closed`
  - State change event emitters
- [x] Implement auth message sender:
  ```typescript
  ws.onopen = () => {
    ws.send(JSON.stringify({
      type: 'auth',
      id: generateMessageId(),
      timestamp: new Date().toISOString(),
      payload: { token: getAccessToken() }
    }));
  };
  ```
- [x] Add 5-second auth timeout handler:
  - Show "Authenticating..." status
  - Handle timeout with user-friendly error
- [x] Queue messages until authenticated:
  - Buffer chat messages during auth
  - Send queued messages after auth success

#### Re-authentication Implementation
- [x] Listen for `auth_required` messages from server
- [x] Automatically refresh token via `/v1/auth/refresh`
- [x] Send new auth message without user intervention
- [x] Maintain active chat state during re-auth
- [ ] Show subtle "Refreshing connection..." indicator

#### UI/UX Changes
- [x] Add connection status indicator:
  - Green: Connected and authenticated
  - Yellow: Authenticating or re-authenticating  
  - Red: Disconnected or auth failed
- [ ] Update error messages:
  - "Connecting to chat..." → "Authenticating..."
  - "Authentication failed. Please try again."
  - "Session expired. Refreshing..."
- [x] Implement graceful degradation:
  - Disable send button during auth
  - Show offline mode for connection issues
  - Auto-retry with exponential backoff

#### Frontend Testing
- [x] Unit tests for state machine transitions
- [x] Mock WebSocket for auth flow testing
- [x] Test message queueing during auth
- [x] Test automatic token refresh
- [ ] E2E tests with real WebSocket connection

### Phase 6: Client Compatibility & Migration
- [ ] Create backward compatibility layer:
  - Feature flag to toggle auth methods
  - Detect old clients by initial message
  - Log deprecation warnings
- [ ] Update API documentation with examples
- [ ] Create migration guide with code samples
- [ ] Add TypeScript types for all message formats
- [ ] Version the WebSocket protocol (v2)

### Phase 7: Monitoring and Error Handling
- [x] Add metrics for auth success/failure rates
- [x] Log authentication timeout events
- [x] Add detailed error messages for different auth failures
- [x] Monitor re-authentication success rates

## Breaking Changes
1. All WebSocket clients must update to send auth message
2. Header/query parameter auth will no longer work
3. Connection flow changes from immediate to deferred auth

## Rollback Plan
1. Keep old auth code in separate function temporarily
2. Add feature flag to toggle between auth methods
3. Monitor error rates during rollout
4. Quick revert possible by changing feature flag

## Testing Strategy
1. Unit tests for each connection state
2. Integration tests for full auth flow
3. Load tests for concurrent auth timeouts
4. End-to-end tests with real JWT tokens
5. Chaos testing for re-auth edge cases

## Security Considerations
- 5-second window limits brute force attempts
- Connection tracking prevents auth message replay
- Token refresh prevents long-lived connections
- Rate limiting on auth messages per IP

## Performance Impact
- Slight increase in connection setup time
- Additional memory for connection state tracking
- Background tasks for timeout and re-auth checks
- Negligible impact expected (<50ms added latency)

## Timeline Estimate
- Phase 1 (Core Backend): 4 hours
- Phase 2 (Message Format): 2 hours  
- Phase 3 (Re-authentication): 6 hours
- Phase 4 (Backend Tests): 4 hours
- Phase 5 (Frontend Implementation): 8 hours
- Phase 6 (Compatibility): 3 hours
- Phase 7 (Monitoring): 2 hours
- **Total: ~29 hours**

### Frontend Breakdown:
- WebSocket client updates: 3 hours
- Re-authentication logic: 2 hours
- UI/UX changes: 2 hours
- Frontend testing: 1 hour

## Frontend Code Examples

### WebSocket Connection Manager
```typescript
class WebSocketManager {
  private state: 'connecting' | 'authenticating' | 'authenticated' | 'reconnecting' | 'closed';
  private ws: WebSocket | null = null;
  private messageQueue: QueuedMessage[] = [];
  private authTimeout: NodeJS.Timeout | null = null;

  connect(recipeId: string) {
    this.state = 'connecting';
    this.ws = new WebSocket(`wss://${API_URL}/v1/chat/${recipeId}`);
    
    this.ws.onopen = () => {
      this.state = 'authenticating';
      this.sendAuthMessage();
      this.startAuthTimeout();
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (this.state === 'authenticating' && message.type === 'recipe_update') {
        this.onAuthenticated();
      } else if (message.type === 'auth_required') {
        this.handleReauthentication();
      }
      // ... handle other messages
    };
  }

  private sendAuthMessage() {
    const token = localStorage.getItem('access_token');
    this.send({
      type: 'auth',
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      payload: { token }
    });
  }

  private startAuthTimeout() {
    this.authTimeout = setTimeout(() => {
      this.handleAuthTimeout();
    }, 5000);
  }

  private async handleReauthentication() {
    try {
      const newToken = await refreshAccessToken();
      this.sendAuthMessage();
    } catch (error) {
      this.disconnect('Failed to refresh authentication');
    }
  }
}
```

### React Hook Example
```typescript
export function useWebSocketChat(recipeId: string) {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const wsManager = useRef<WebSocketManager>();

  useEffect(() => {
    wsManager.current = new WebSocketManager();
    
    wsManager.current.on('stateChange', setConnectionState);
    wsManager.current.on('message', (msg) => setMessages(prev => [...prev, msg]));
    
    wsManager.current.connect(recipeId);

    return () => wsManager.current?.disconnect();
  }, [recipeId]);

  const sendMessage = useCallback((content: string) => {
    if (connectionState !== 'authenticated') {
      showToast('Please wait for connection...');
      return;
    }
    wsManager.current?.sendChatMessage(content);
  }, [connectionState]);

  return { connectionState, messages, sendMessage };
}
```

## Dependencies
- No new backend package dependencies
- Frontend may need event emitter library
- Requires coordination with frontend team
- API documentation must be updated first

## Risks
- **High**: Breaking change for all WebSocket clients
- **Medium**: Increased complexity in connection handling
- **Low**: Performance degradation from state tracking