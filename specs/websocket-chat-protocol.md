# WebSocket Chat Protocol (v0.1)

> **Purpose**: Define the bidirectional message protocol for real-time recipe editing via chat interface.

---

## 1. Connection Lifecycle

### 1.1 Connection URL
```
wss://recipe-chat-assistant--fastapi-app.modal.run/v1/chat/{recipeId}
```

### 1.2 Authentication
- Client establishes WebSocket connection without authentication
- Client must send authentication message as first message after connection
- Server validates token and recipe ownership before accepting further messages
- Connection closed with code 1008 (Policy Violation) if unauthorized
- Authentication timeout: 5 seconds after connection established

### 1.3 Re-authentication
- Server tracks JWT token expiration for each connection
- At 14 minutes (before 15-minute token expiry), server sends `auth_required` message
- Client automatically refreshes token via `/v1/auth/refresh` endpoint
- Client sends new token in `auth` message without user intervention
- If re-authentication fails, connection closed with code 1008

### 1.4 Connection States
1. **Connecting** - WebSocket handshake in progress
2. **Authenticating** - Waiting for auth message
3. **Connected** - Authenticated and ready for messages
4. **Reconnecting** - Auto-retry after disconnect
5. **Closed** - Terminated by client or server

## 2. Message Format

All messages are JSON with this envelope:

```json
{
  "type": "string",       // Message type identifier
  "id": "string",         // Unique message ID (UUID)
  "timestamp": "string",  // ISO-8601 timestamp
  "payload": {}          // Type-specific data
}
```

## 3. Client → Server Messages

### 3.1 Authentication Message
```json
{
  "type": "auth",
  "id": "auth_123",
  "timestamp": "2025-06-23T10:00:00Z",
  "payload": {
    "token": "eyJ..."
  }
}
```

**Usage**: 
- Must be first message after connection established
- Also sent in response to `auth_required` message from server
- Contains valid JWT access token

### 3.2 Chat Message
```json
{
  "type": "chat_message",
  "id": "msg_123",
  "timestamp": "2025-06-23T10:00:00Z",
  "payload": {
    "content": "Make this recipe vegan"
  }
}
```

**Usage**: All user chat input, including:
- Recipe extraction requests ("Extract recipe from: [pasted text]")
- Recipe generation requests ("Create a pasta recipe for 4 people")
- Recipe modification requests ("Make this recipe vegan", "Add more protein")
- General questions and refinements

## 4. Server → Client Messages

### 4.1 Authentication Required
```json
{
  "type": "auth_required",
  "id": "msg_199",
  "timestamp": "2025-06-23T10:14:00Z",
  "payload": {
    "reason": "Token expiring soon"
  }
}
```

**Usage**: 
- Sent when JWT token is about to expire (at ~14 minutes)
- Client should immediately fetch new token and send auth message
- No other messages accepted until re-authenticated

### 4.2 Recipe Update
```json
{
  "type": "recipe_update",
  "id": "msg_200",
  "timestamp": "2025-06-23T10:00:10Z",
  "payload": {
    "request_id": "msg_123",  // Links to original chat_message
    "content": "I'll help you make this recipe vegan. Here are the changes:",
    "recipe_data": {
      // Full updated recipe JSON matching recipe-schema.json
      "title": "Vegan Pasta Recipe",
      "yield": "4 servings",
      "ingredients": [
        {"text": "2 cups oat milk", "quantity": 2, "unit": "cup"}
      ],
      "steps": [
        {"order": 1, "text": "Heat the oat milk in a pan"}
      ]
    }
  }
}
```

**Usage**: All server responses including:
- Recipe extraction results with structured recipe data
- Recipe generation results with new recipe data  
- Recipe modification results with updated recipe data
- Assistant chat responses with or without recipe changes
- Error messages when processing fails

## 5. Message Flow Examples

### 5.1 Initial Connection & Authentication
```
Client: Connect to WebSocket
Client: auth (JWT token)
Server: (validates token, ready for messages)
```

### 5.2 Re-authentication Flow
```
Server: auth_required (token expiring soon)
Client: (fetches new token via /v1/auth/refresh)
Client: auth (new JWT token)
Server: (validates token, continues normal operation)
```

### 5.3 Recipe Extraction
```
Client: chat_message ("Extract recipe from: [pasted recipe text]")
Server: recipe_update (extracted structured recipe with content explaining extraction)
```

### 5.4 Recipe Modification  
```
Client: chat_message ("Make this recipe vegan")
Server: recipe_update (modified recipe with vegan substitutions + explanation)
```

### 5.5 Recipe Generation
```
Client: chat_message ("Create a pasta recipe for 4 people")
Server: recipe_update (new generated recipe + explanation)
```

### 5.6 Error Handling
```
Client: chat_message ("make this gluten-free")
Server: recipe_update (error content explaining LLM processing failed)
```

### 5.7 Incomplete Recipe Handling
```
Client: chat_message ("Extract recipe from: Chocolate cake with flour and eggs")
Server: recipe_update (content requesting more info, recipe_data: null)
```

## 6. Error Handling

### 6.1 Connection Errors
- Basic reconnection on disconnect (browser WebSocket default behavior)
- Display "Connection lost" message to user with retry button
- Resume with current recipe state after reconnection

### 6.2 Message Processing Errors
All errors are communicated via `recipe_update` messages with error content:

```json
{
  "type": "recipe_update",
  "payload": {
    "request_id": "msg_123",
    "content": "Sorry, I couldn't process that request. Please try again.",
    "recipe_data": null  // No recipe changes when error occurs
  }
}
```

**Error Scenarios:**
- Invalid JSON from LLM → "Unable to understand the recipe format"
- LLM timeout → "Request took too long, please try again"  
- Rate limiting → "Too many requests, please wait a moment"
- Initial auth failure → Close connection with code 1008
- Re-auth failure → Close connection with code 1008, redirect to login
- Incomplete recipe data → "I need more information. Could you provide the cooking steps?"

## 7. Rate Limits

- Max 30 messages/minute per connection
- Max 5 concurrent connections per user  
- Max message size: 64KB

---

*End of WebSocket Chat Protocol v0.1*