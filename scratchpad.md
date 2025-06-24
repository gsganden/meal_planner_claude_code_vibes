# Recipe Chat Assistant - Development Scratchpad

## Session Date: June 24, 2025

## Overview
This session focused on debugging and fixing WebSocket connection issues, implementing auto-reload for development, and resolving API rate limiting issues.

## Major Issues Resolved

### 1. WebSocket Rapid Reconnection Issue
**Problem**: WebSocket was reconnecting rapidly, going "back and forth between trying to connect and failing to connect"

**Root Cause**: React hook dependencies causing unnecessary re-renders
- The `useWebSocket` hook was recreating the WebSocket connection on every component re-render
- Unstable dependencies in `useCallback` and `useEffect` were the culprits

**Solution**: 
- Used `useRef` to stabilize callback dependencies
- Removed unstable dependencies from `useEffect`
- Ensured WebSocket only reconnects when the actual recipe ID changes

**Files Modified**:
- `frontend/src/hooks/useWebSocket.ts`

### 2. WebSocket Authentication & Connection Issues
**Problem**: WebSocket connections were failing with authentication errors and JSON serialization errors

**Issues Found**:
1. CORS configuration didn't include port 3001 when frontend restarted
2. UUID objects weren't being properly serialized to JSON
3. Authentication tokens weren't being passed correctly

**Solutions**:
1. Updated CORS configuration in `modal_app.py` to include multiple ports
2. Created custom `UUIDEncoder` for JSON serialization
3. Changed `.dict()` calls to `.model_dump(mode='json')` for Pydantic models

**Files Modified**:
- `modal_app.py` - CORS configuration
- `src/chat/websocket.py` - Added UUIDEncoder and fixed serialization
- `frontend/.env` - Updated WebSocket URLs

### 3. LLM Rate Limiting (429 Errors)
**Problem**: Google Gemini API quota exhausted with 429 errors

**Solution**: 
- Switched from `gemini-2.5-pro` to `gemini-2.5-flash` (cheaper, higher rate limits)
- Added configuration reload mechanism to pick up changes without restart

**Files Modified**:
- `llm_registry.yaml` - Changed all models to use Flash variants
- `src/llm/prompt_loader.py` - Added reload functionality
- `src/llm/client.py` - Added reload calls before LLM requests

## Development Environment Setup

### Auto-Reload Configuration
**Frontend**: Vite HMR already provides hot module replacement
**Backend**: `modal serve` provides auto-reload with file watching

**Commands**:
```bash
# Frontend (auto-reload built-in)
cd frontend && npm run dev

# Backend (auto-reload with Modal serve)
modal serve modal_app.py
```

**URLs**:
- Production: `https://gsganden--recipe-chat-assistant-fastapi-app.modal.run`
- Development: `https://gsganden--recipe-chat-assistant-fastapi-app-dev.modal.run`

## Gotchas & Lessons Learned

1. **Modal Deployment Caching**: Modal can cache configurations. The `prompt_loader` was a global instance that loaded configuration only once, causing the old model to persist even after config changes.

2. **Virtual Environment Issues**: The `.venv/bin/activate` script wasn't executable initially. Fixed with `chmod +x`.

3. **Port Conflicts**: Frontend dev server switched between ports 3000/3001 when restarting, requiring CORS updates.

4. **WebSocket Protocol Implementation**: The WebSocket reconnection logic requires careful implementation of exponential backoff per the spec (1s, 2s, 4s, 8s, max 30s).

5. **React Hook Dependencies**: Unstable dependencies in hooks can cause infinite re-render loops. Using refs is crucial for callbacks that shouldn't trigger re-renders.

6. **JSON Serialization**: Python UUID and datetime objects need custom JSON encoders. Pydantic's `.model_dump(mode='json')` handles this automatically.

## Judgment Calls Made

1. **Development vs Production Databases**: Modal serve uses a separate database from production, requiring new user registration and recipe creation in dev.

2. **Error Messaging**: Added user-friendly error messages for rate limiting instead of generic "couldn't process" messages.

3. **Configuration Reloading**: Added automatic configuration reloading to all LLM methods to ensure changes take effect without restart.

4. **Model Selection**: Chose Gemini 2.5 Flash over Pro for cost efficiency and higher rate limits on free tier.

## Key Files Discovered

1. **WebSocket Implementation**:
   - `src/chat/websocket.py` - Backend WebSocket handler
   - `frontend/src/services/websocket.ts` - Frontend WebSocket client
   - `frontend/src/hooks/useWebSocket.ts` - React hook for WebSocket

2. **LLM Configuration**:
   - `llm_registry.yaml` - Model configurations
   - `src/llm/client.py` - LLM client implementation
   - `src/llm/prompt_loader.py` - Prompt and model configuration loader

3. **Authentication**:
   - `src/auth/jwt_handler.py` - JWT token handling

4. **Tests**:
   - `tests/test_websocket_chat.py` - WebSocket protocol tests

## Questions Answered

1. **Q**: Why is the WebSocket reconnecting rapidly?
   **A**: React hook dependencies were causing component re-renders, triggering new WebSocket connections.

2. **Q**: Why are we getting UUID serialization errors?
   **A**: Default JSON encoder doesn't handle UUID objects. Need custom encoder or Pydantic's model_dump.

3. **Q**: How to enable auto-reload for development?
   **A**: Use `modal serve` instead of `modal deploy` for backend auto-reload.

4. **Q**: Why is the LLM returning "couldn't process request"?
   **A**: API rate limits exceeded (429 errors) on Gemini Pro free tier.

## Outstanding Questions

1. Should we implement a fallback to a local LLM when API rate limits are hit?
2. Should we add retry logic with exponential backoff for LLM requests?
3. Should we implement WebSocket connection state persistence across page refreshes?
4. Should we add monitoring/alerting for API rate limit errors?

## Next Steps

1. Consider implementing proper error handling UI for rate limit errors
2. Add connection status indicators in the UI
3. Implement message retry queue for failed LLM requests
4. Consider adding API usage tracking to prevent hitting rate limits
5. Update Modal deprecation warnings (switch to new parameter names)

## Environment Details
- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI + Modal + SQLite
- **LLM**: Google Gemini API (switched from 2.5 Pro to 2.5 Flash)
- **WebSocket**: Custom implementation following chat protocol spec
- **Authentication**: JWT tokens