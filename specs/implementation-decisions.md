# Implementation Decisions (v0.1)

> **Purpose**: Document specific implementation choices made during development that weren't explicitly specified in the original specs.

---

## 1. Project Structure

**Decision**: Use standard Python project structure with Modal deployment
```
/
├── src/
│   ├── api/           # FastAPI application
│   ├── auth/          # Authentication logic
│   ├── chat/          # WebSocket chat handling
│   ├── llm/           # LLM integration
│   ├── models/        # Pydantic models
│   └── db/            # Database operations
├── tests/             # Test suite
├── prompts/           # LLM prompt templates
├── requirements.txt   # Python dependencies
├── modal_app.py       # Modal deployment entry point
└── llm_registry.yaml  # LLM configuration
```

**Rationale**: Separation of concerns, testable modules, clear Modal deployment path

## 2. Database Connection

**Decision**: Use asyncpg with connection pooling
**Rationale**: Async support for FastAPI, better performance than sync drivers

## 3. Authentication Implementation

**Decision**: Use Auth0 for OAuth + magic links, implement JWT handling in-app
**Rationale**: Reduces auth complexity, proven OAuth flows, flexible JWT management

## 4. Environment Configuration

**Decision**: Use Pydantic Settings for configuration management
**Rationale**: Type safety, validation, clear environment variable mapping

## 5. Testing Strategy

**Decision**: 
- Unit tests with pytest
- Integration tests with TestClient  
- LLM tests with mock responses
- WebSocket tests with test client
- Database tests with SQLite in-memory
- Test against specs, not implementation details

**Rationale**: Comprehensive coverage without external dependencies in tests

## 6. Authentication Simplification (MVP)

**Decision**: Simplified auth flow for MVP
- Magic link: token = email address
- OAuth: token = "oauth:email@domain.com"
- No actual Auth0 integration yet

**Rationale**: Focus on core functionality, real Auth0 integration post-MVP

## 7. LLM Error Handling

**Decision**: Graceful fallback with user-friendly messages
- Invalid JSON responses handled with error messages
- Network failures return helpful error responses
- Fallback prompts if templates not found

**Rationale**: User experience over perfect functionality

---

*Updated during implementation*