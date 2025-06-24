# Recipe Chat Assistant Reimplementation Plan

## Overview
Complete reimplementation of the Recipe Chat Assistant following the specifications while incorporating critical learnings from the previous implementation. Current main branch has only specs and frontend components; backend needs full implementation.

## Phase 1: Foundation & Environment Setup (Week 1)

### 1.1 Authentication System (As Per Specs)
**Specs Requirement**: Traditional email/password with JWT tokens (NOT Auth0 for MVP)
- Implement `POST /v1/auth/signup` with email/password validation
- Implement `POST /v1/auth/signin` with bcrypt password verification
- Add JWT token generation with access/refresh token pairs
- Implement password reset flow with email tokens
- Add proper input validation and user-friendly error messages

**Key Learning Applied**: Fix React hook dependencies to prevent authentication state loops

### 1.2 Database Architecture
**Specs Requirement**: SQLite on Modal Volume with JSONB recipe storage
- Set up SQLite with Modal Volume mounting at `/data`
- Create users table (id, email, password_hash, name, created_at) 
- Create recipes table (id, owner_id, recipe_data JSONB, created_at, updated_at)
- Implement recipe JSONB validation against recipe-schema.json

**Key Learning Applied**: Use `.model_dump(mode='json')` for Pydantic serialization, custom UUIDEncoder for JSON

### 1.3 Project Structure
```
src/
├── api/           # FastAPI routers
├── auth/          # JWT and password handling  
├── chat/          # WebSocket implementation
├── llm/           # Gemini integration
├── models/        # Pydantic models
├── db/            # Database operations
└── core/          # Config and dependencies
```

## Phase 2: Core API Implementation (Week 2)

### 2.1 Recipe CRUD API
**Specs Requirement**: Full REST API following api-contract.yaml
- `GET /v1/recipes` - List user recipes in reverse chronological order
- `POST /v1/recipes` - Create with auto-generated "Untitled Recipe {N}" title
- `GET /v1/recipes/{id}` - Fetch specific recipe
- `PATCH /v1/recipes/{id}` - Update recipe fields
- `DELETE /v1/recipes/{id}` - Delete recipe
- User-scoped access with JWT authentication

### 2.2 LLM Integration
**Specs Requirement**: Google Gemini 2.5 Pro via OpenAI-compatible API
- Configure Google Gemini endpoint with proper API key
- Implement prompt templates from `/prompts` directory
- Add recipe extraction from text functionality
- Add recipe generation from natural language
- Handle graceful fallbacks and error responses

**Key Learning Applied**: Use Gemini 2.5 Flash for higher rate limits, add reload mechanism for config changes

## Phase 3: WebSocket Chat Protocol (Week 2-3)

### 3.1 WebSocket Implementation
**Specs Requirement**: Follow websocket-chat-protocol.md exactly
- Implement bidirectional message protocol with proper JSON envelope
- Support message types: chat_message, field_update, action_request, heartbeat
- Add JWT authentication for WebSocket connections
- Implement user-scoped recipe access validation

**Key Learning Applied**: Implement exponential backoff (1s, 2s, 4s, 8s, max 30s), fix frontend hook dependencies

### 3.2 Real-time Recipe Updates
- Stream recipe changes live to frontend
- Handle field updates with conflict resolution
- Implement message queuing during disconnections
- Add processing status indicators

## Phase 4: Frontend Integration (Week 3)

### 4.1 Authentication UI
**Specs Requirement**: Traditional email/password forms with validation
- Create sign-up/sign-in toggle forms
- Implement real-time validation (email format, password strength)
- Add proper loading states and error handling  
- Implement session management with localStorage

**Key Learning Applied**: Proper form state management, clear error messaging

### 4.2 Recipe Editor Interface
**Specs Requirement**: Two-pane layout (chat 40%, recipe form 60%)
- Implement live recipe preview during chat
- Add direct field editing with chat sync
- Create auto-save with 2-second debounce
- Add "Saving..." and "Saved" indicators

### 4.3 Recipe List Interface
- Display recipes in reverse chronological order
- Show title, description, last updated
- Implement "New Recipe" with immediate creation
- Add proper navigation and back buttons

## Phase 5: Production Deployment (Week 4)

### 5.1 Modal Deployment
**Specs Requirement**: SQLite on Modal Volume
- Set up Modal Volume for persistent storage
- Configure Modal secrets for API keys and JWT secrets
- Implement proper CORS for production domains
- Add health check endpoints

**Key Learning Applied**: Update Modal deprecated parameter names, fix CORS port configurations

### 5.2 Environment Configuration
- Migrate from Auth0 to simple email/password
- Use Google Gemini API with proper base URL
- Configure production vs development environments
- Set up proper secret management

## Key Specifications to Follow

### Authentication (NOT Auth0)
- Traditional email/password signup/signin
- JWT access/refresh token pairs
- Password requirements: min 8 chars, letter + number
- bcrypt with salt rounds ≥12

### Database Schema
- Users: id, email, password_hash, name, created_at
- Recipes: id, owner_id, recipe_data (JSONB), created_at, updated_at  
- Recipe JSONB follows recipe-schema.json exactly

### API Contract
- Follow api-contract.yaml specification exactly
- All endpoints user-scoped with JWT Bearer auth
- Proper HTTP status codes and error responses
- Recipe CRUD with patch support

### WebSocket Protocol
- Follow websocket-chat-protocol.md message format
- Support all required message types
- Implement proper reconnection with exponential backoff
- JWT authentication for connections

## Critical Learnings to Apply

1. **React Hook Dependencies**: Use `useRef` for stable callbacks, avoid unstable dependencies in `useEffect`
2. **JSON Serialization**: Use Pydantic `.model_dump(mode='json')` and custom UUIDEncoder  
3. **LLM Rate Limits**: Use Gemini Flash models, implement config reload mechanism
4. **CORS Configuration**: Include all development ports, handle port switching
5. **Modal Deployment**: Use proper volume mounting, update deprecated parameters
6. **WebSocket Reconnection**: Implement spec-compliant exponential backoff
7. **Error Handling**: User-friendly messages, proper fallbacks for API failures

## Testing Strategy
- Unit tests for all core functionality
- Integration tests for LLM and database operations  
- WebSocket protocol compliance tests
- Authentication flow tests
- End-to-end recipe creation workflows

## Success Criteria
- ✅ Authentication works with email/password (no Auth0)
- ✅ Recipe CRUD operations follow API contract exactly  
- ✅ WebSocket chat enables real-time recipe editing
- ✅ LLM integration extracts/generates recipes reliably
- ✅ SQLite on Modal Volume persists data correctly
- ✅ Frontend provides smooth chat-driven recipe creation
- ✅ All specifications are implemented as designed

This plan prioritizes implementing the app exactly as specified while incorporating all the hard-won lessons from the previous implementation attempts.