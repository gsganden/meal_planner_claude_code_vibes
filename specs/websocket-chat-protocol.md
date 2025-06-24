# WebSocket Chat Protocol (v0.1)

> **Purpose**: Define the bidirectional message protocol for real-time recipe editing via chat interface.

---

## 1. Connection Lifecycle

### 1.1 Connection URL
```
wss://api.myrecipes.app/v1/chat/{recipeId}
```

### 1.2 Authentication
- Client must include JWT Bearer token in connection headers
- Server validates token and recipe ownership before accepting connection
- Connection rejected with 401 if unauthorized

### 1.3 Connection States
1. **Connecting** - WebSocket handshake in progress
2. **Connected** - Ready for messages
3. **Reconnecting** - Auto-retry after disconnect
4. **Closed** - Terminated by client or server

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

### 3.1 Chat Message
```json
{
  "type": "chat_message",
  "id": "msg_123",
  "timestamp": "2025-06-23T10:00:00Z",
  "payload": {
    "content": "Make this recipe vegan",
    "context": {
      // Optional: additional context for the request
    }
  }
}
```

### 3.2 Field Update
```json
{
  "type": "field_update",
  "id": "msg_124",
  "timestamp": "2025-06-23T10:01:00Z",
  "payload": {
    "field_path": "ingredients[2].quantity",
    "value": "2",
    "previous_value": "3"
  }
}
```

### 3.3 Action Request
```json
{
  "type": "action_request",
  "id": "msg_125",
  "timestamp": "2025-06-23T10:02:00Z",
  "payload": {
    "action": "scale_recipe",  // scale_recipe, convert_units, substitute_ingredient
    "parameters": {
      "servings": 4
    }
  }
}
```

### 3.4 Heartbeat
```json
{
  "type": "heartbeat",
  "id": "msg_126",
  "timestamp": "2025-06-23T10:03:00Z",
  "payload": {}
}
```

## 4. Server → Client Messages

### 4.1 Chat Response
```json
{
  "type": "chat_response",
  "id": "msg_200",
  "timestamp": "2025-06-23T10:00:05Z",
  "payload": {
    "request_id": "msg_123",  // Links to original request
    "content": "I'll help you make this recipe vegan. Here are the substitutions:",
    "suggestions": [
      {
        "field_path": "ingredients[1]",
        "original": {"text": "2 cups milk", "quantity": 2, "unit": "cup"},
        "suggested": {"text": "2 cups oat milk", "quantity": 2, "unit": "cup"}
      }
    ]
  }
}
```

### 4.2 Recipe Update
```json
{
  "type": "recipe_update",
  "id": "msg_201",
  "timestamp": "2025-06-23T10:00:10Z",
  "payload": {
    "changes": [
      {
        "field_path": "ingredients[1].text",
        "value": "2 cups oat milk"
      }
    ],
    "recipe_data": {} // Full recipe JSON
  }
}
```

### 4.3 Processing Status
```json
{
  "type": "processing_status",
  "id": "msg_202",
  "timestamp": "2025-06-23T10:00:02Z",
  "payload": {
    "request_id": "msg_123",
    "status": "processing",  // processing, completed, failed
    "message": "Analyzing recipe for vegan substitutions..."
  }
}
```

### 4.4 Error
```json
{
  "type": "error",
  "id": "msg_203",
  "timestamp": "2025-06-23T10:00:15Z",
  "payload": {
    "request_id": "msg_123",
    "code": "llm_error",
    "message": "Unable to process request. Please try again."
  }
}
```

### 4.5 System Message
```json
{
  "type": "system_message",
  "id": "msg_204",
  "timestamp": "2025-06-23T10:00:20Z",
  "payload": {
    "level": "info",  // info, warning, error
    "message": "Another user is editing this recipe"
  }
}
```

## 5. Message Flow Examples

### 5.1 Chat-Driven Edit
```
Client: chat_message ("make vegan")
Server: processing_status ("analyzing...")
Server: chat_response (with suggestions)
Client: action_request ("apply_suggestions")
Server: recipe_update (updated recipe)
```

### 5.2 Direct Field Edit
```
Client: field_update (ingredients[0].quantity = "3")
Server: recipe_update (confirmed change)
Server: system_message ("field updated")
```

## 6. Error Handling

### 6.1 Connection Errors
- Auto-reconnect with exponential backoff: 1s, 2s, 4s, 8s, max 30s
- Preserve message queue during reconnection
- Resume with current recipe state

### 6.2 Message Errors
| Error Code | Description | Client Action |
|------------|-------------|---------------|
| `invalid_message` | Malformed JSON or missing fields | Fix and retry |
| `unauthorized` | Token expired or invalid recipe | Refresh auth |
| `rate_limit` | Too many messages | Backoff 1 minute |
| `llm_error` | AI processing failed | Retry or fallback |

## 7. Rate Limits

- Max 30 messages/minute per connection
- Max 5 concurrent connections per user
- Max message size: 64KB

## 8. Keep-Alive

- Client sends heartbeat every 30s
- Server responds with heartbeat_ack
- Connection closed if no heartbeat for 90s

---

*End of WebSocket Chat Protocol v0.1*