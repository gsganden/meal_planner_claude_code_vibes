# Recipe Chat Assistant Implementation Plan

## Phase 1: Foundation & Core Setup (Week 1)

### 1.1 Project Structure & Environment
- [x] Create clean project structure with proper directories
  - [x] `src/api/` - FastAPI routes
  - [x] `src/auth/` - JWT authentication
  - [x] `src/chat/` - WebSocket handlers  
  - [x] `src/db/` - Database operations
  - [x] `src/llm/` - LLM integration
  - [x] `src/models/` - Pydantic models
  - [x] `tests/` - Comprehensive test suite
  - [x] `prompts/` - LLM prompt templates
- [x] Set up virtual environment with executable permissions (`chmod +x .venv/bin/activate`)
- [x] Use `modal serve` for development auto-reload (not `modal deploy`)
- [x] Configure CORS for multiple frontend ports (3000, 3001)

### 1.2 Database Foundation
- [x] Implement SQLite with aiosqlite for async support
- [x] Create two-table schema (users, recipes) with JSONB recipe storage
- [x] Use `func.json_extract()` for SQLite JSON operations (not PostgreSQL syntax)
- [x] Implement custom JSON encoder for UUID serialization
- [x] Set up Modal Volume for SQLite persistence

### 1.3 Authentication System
- [x] Implement email/password authentication (NOT Auth0)
- [x] Create endpoints: `/v1/auth/signup`, `/v1/auth/signin`, `/v1/auth/refresh`, `/v1/auth/logout`
- [x] Add password reset endpoints: `/v1/auth/forgot-password`, `/v1/auth/reset-password`
- [x] **CRITICAL**: Store JWT expiration as Unix timestamp, not datetime objects
- [x] Implement bcrypt with ≥12 salt rounds
- [x] Enforce password requirements (min 8 chars, letter + number)

## Phase 2: API & LLM Integration (Week 2)

### 2.1 Recipe CRUD API
- [x] Implement all endpoints following `api-contract.yaml` exactly
- [x] Ensure all endpoints are user-scoped with JWT authentication
- [x] Add recipe schema validation against `recipe-schema.json`
- [x] Enforce minimum completeness: title, yield, ≥1 ingredient, ≥1 step
- [x] Implement auto-generated titles: "Untitled Recipe {N}"

### 2.2 LLM Integration
- [x] Configure Gemini 2.5 Flash (better rate limits than Pro)
- [x] Use Google's OpenAI-compatible endpoint
- [x] Ensure responses return valid JSON conforming to recipe schema
- [x] Implement graceful error handling with user-friendly messages
- [x] Add configuration reload mechanism to avoid cached model settings

### 2.3 Testing Strategy
- [x] **CRITICAL**: Use AsyncClient (httpx) for async FastAPI testing, not TestClient
- [x] Mock LLM calls at import locations (`src.chat.websocket.get_llm_client`)
- [x] Add `@pytest.mark.asyncio` decorators to all async test methods
- [x] Write tests against specifications, not implementation details
- [x] Achieve comprehensive test coverage for core functionality

## Phase 3: WebSocket Chat Implementation (Week 3)

### 3.1 Simplified Protocol
- [x] Implement 2 message types only:
  - [x] `chat_message` (client→server) - all user input
  - [x] `recipe_update` (server→client) - all responses including errors
- [x] **CRITICAL**: TestClient WebSocket methods are synchronous - don't use `await`
- [x] Handle all interactions through these types (extraction, generation, modification, errors)

### 3.2 Real-time Recipe Editing
- [x] Implement live preview updates via `recipe_update` messages
- [x] Handle incomplete recipes with helpful prompts (`recipe_data: null`)
- [x] Add basic reconnection with "Connection lost" UI feedback
- [x] Implement WebSocket authentication with JWT tokens in headers

### 3.3 React WebSocket Integration
- [x] Create stable React hook dependencies using useRef (prevent rapid reconnections)
- [x] Implement proper connection state management
- [x] Add exponential backoff for reconnection (1s, 2s, 4s, 8s, max 30s)

## Phase 4: Frontend Integration (Week 4)

### 4.1 React Application
- [x] Build authentication forms with real-time validation
  - [x] Email format validation on blur
  - [x] Password strength indicators
  - [x] Form state management with submit button enabling
- [x] Create two-pane recipe editor (chat + live preview)
- [x] Implement Zustand for auth state management
- [x] Use React hooks for recipe data management

### 4.2 Error Handling & UX
- [x] Display user-friendly error messages for:
  - [x] Rate limits: "Too many requests, please wait a moment"
  - [x] Timeouts: "Request took too long, please try again"
  - [x] Validation failures: "Unable to understand the recipe format"
- [x] Add loading states during LLM processing
- [x] Implement browser back button handling
- [x] Add unsaved changes warnings
- [x] Create auto-save with 2-second debounce and visual feedback

### 4.3 Navigation & State Management
- [x] Implement proper URL routing (`/recipe/{id}`)
- [x] Handle multi-tab/window scenarios
- [x] Add recipe deletion with confirmation dialogs
- [x] Create recipe list with chronological ordering

## Phase 5: Deployment & Production (Week 5)

### 5.1 Modal Deployment
- [ ] Set up separate dev/production databases on Modal
- [ ] Configure Modal secrets for API keys and JWT secrets
- [ ] Implement SQLite persistence on Modal Volume
- [ ] Add `/health` endpoint for monitoring
- [ ] Set up proper environment variable management

### 5.2 Email Service Integration
- [ ] Integrate SMTP or email API service for password reset
- [ ] Implement time-limited tokens (1 hour expiration)
- [ ] Ensure single-use token validation
- [ ] Add rate limiting for email sending
- [ ] Create user-friendly email templates

### 5.3 Production Readiness
- [ ] Run comprehensive test suite (target: 100+ tests passing)
- [ ] Implement security checklist requirements
- [ ] Set up monitoring and logging via Modal
- [ ] Configure rate limiting per security specifications
- [ ] Test full user workflow end-to-end

## Critical Implementation Guidelines

### ✅ Essential Do's
- [ ] Follow specifications exactly - they're comprehensive and tested
- [x] Use simplified WebSocket protocol - 2 message types cover all needs
- [x] Mock LLM calls in tests - patch at import locations to avoid API costs
- [x] Use AsyncClient for testing - proper async patterns with httpx
- [x] Implement proper UUID/datetime JSON serialization using Pydantic model_dump
- [x] Focus on user-friendly error messages per specifications

### ❌ Critical Don'ts
- [ ] ~~Don't add Auth0 complexity~~ - stick to email/password JWT
- [ ] ~~Don't implement file upload features~~ - out of scope for MVP
- [ ] ~~Don't use complex versioning~~ - simplified approach for MVP
- [ ] ~~Don't ignore CORS configuration~~ - support multiple frontend ports
- [ ] ~~Don't mix sync/async patterns~~ - be consistent with async throughout

## Risk Mitigation Checklist

### High-Risk Areas
- [ ] **LLM Rate Limiting**: Use Gemini 2.5 Flash, implement proper error handling
- [ ] **WebSocket Stability**: Use proven reconnection patterns, stable React hooks
- [ ] **JWT Token Handling**: Store as Unix timestamps, proper expiration checks  
- [ ] **Database Operations**: Use SQLite-compatible JSON operations

### Success Metrics
- [ ] 100% test coverage for core functionality
- [ ] All tests passing (auth, API, WebSocket, LLM, database)
- [ ] Real-time chat working with live recipe preview
- [ ] Production deployment on Modal with persistence
- [ ] Complete user workflow: signup → create recipe → chat edit → save

## Implementation Notes

**Previous Success**: This plan is based on a previous implementation that achieved:
- ✅ 100 tests passing (100% success rate)
- ✅ Complete WebSocket protocol implementation  
- ✅ Full authentication system with JWT
- ✅ Comprehensive Recipe CRUD with validation
- ✅ Robust LLM integration with proper mocking
- ✅ Modal deployment with SQLite persistence

**Key Lessons Incorporated**:
- JWT timestamps as Unix time (not datetime objects)
- AsyncClient for testing async FastAPI apps
- LLM mocking at import locations
- WebSocket methods are synchronous in TestClient
- React hook stability with useRef
- Gemini 2.5 Flash for better rate limits
- SQLite JSON operations for cross-platform compatibility
