# CLAUDE.md - Development Notes

## Implementation Details

### Virtual Environment
- Always use project-specific `.venv` (never shared virtual environments)
- Created with: `python -m venv .venv`
- Activate with: `source .venv/bin/activate`

### Key Implementation Decisions

1. **LLM Integration**: Using Google Gemini 2.5 Flash via OpenAI-compatible API
   - Endpoint: `https://generativelanguage.googleapis.com/v1beta/openai/`
   - Uses Google API key, not OpenAI key
   - OpenAI Python library for compatibility

2. **Database**: JSONB storage for recipes
   - SQLite on Modal Volume for production
   - SQLite for local development
   - UUID and JSON types, recipe_data as JSONB

3. **Authentication**: Traditional email/password with JWT tokens
   - Email/password signup and signin
   - JWT access/refresh token pairs
   - bcrypt password hashing with salt rounds ≥12
   - NO Auth0 for MVP

4. **Real-time**: WebSocket chat protocol
   - Message types: chat_message, field_update, action_request, heartbeat
   - Live recipe preview during editing

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_recipe_schema.py -v

# Run tests matching pattern
pytest -k "test_extract" -v
```

### Deployment Workflow
1. Edit `.env` with credentials
2. Run `python setup_modal_secrets.py`
3. Deploy with `python deploy.py`

### Known Issues
- API contract tests fail due to pytest database fixture configuration
- Some WebSocket tests need database dependency injection fixes
- Tests pass individually but have issues in full suite

### Code Style
- Pydantic v2 throughout (no v1 compatibility)
- Type hints on all functions
- Docstrings for classes and public methods
- No comments unless absolutely necessary

## Development Commands

```bash
# Run tests
pytest tests/

# Run specific test suite
pytest tests/test_recipe_schema.py -v

# Run locally (for development)
python modal_app.py

# Check code style
ruff check src/

# Type checking
mypy src/
```

## Environment Variables

For local development, create a `.env` file:

```env
DATABASE_URL=sqlite+aiosqlite:///./local.db
JWT_SECRET_KEY=your-dev-secret-key
GOOGLE_API_KEY=your-google-api-key
GOOGLE_OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
DEBUG=true
```

## API Endpoints

- `GET /health` - Health check
- `POST /v1/auth/signup` - Create new user account
- `POST /v1/auth/signin` - User authentication
- `POST /v1/auth/refresh` - Refresh JWT token
- `POST /v1/auth/logout` - Logout user
- `POST /v1/auth/forgot-password` - Send password reset email
- `POST /v1/auth/reset-password` - Reset password with token
- `GET /v1/recipes` - List user's recipes
- `POST /v1/recipes` - Create new recipe
- `GET /v1/recipes/{id}` - Get specific recipe
- `PATCH /v1/recipes/{id}` - Update recipe
- `DELETE /v1/recipes/{id}` - Delete recipe
- `WebSocket /v1/chat/{recipe_id}` - Real-time recipe chat

## Key Technologies

- **Backend**: FastAPI + SQLAlchemy + Pydantic v2
- **Database**: SQLite on Modal Volume (production) / SQLite (local)
- **LLM**: Google Gemini 2.5 Flash via OpenAI-compatible API
- **Auth**: JWT + email/password
- **Deployment**: Modal
- **Real-time**: WebSockets

## Project Structure

```
meal_planner_claude_code_vibes/
├── .venv/              # Project virtual environment (to be created)
├── src/                # Source code
│   ├── api/           # FastAPI routes
│   ├── auth/          # Authentication logic
│   ├── chat/          # WebSocket handlers
│   ├── db/            # Database models and operations
│   ├── llm/           # LLM integration
│   └── models/        # Pydantic models
├── tests/              # Test suite
├── specs/              # Technical specifications
├── prompts/            # LLM prompt templates
├── modal_app.py        # Modal deployment config
├── requirements.txt    # Python dependencies
└── CLAUDE.md          # This file
```

## Development Process Memorizations

- In general, proceed as follows:
  - Update specs/
  - Write tests against the spec
  - Implement the behavior to pass the tests