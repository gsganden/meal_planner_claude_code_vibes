# Recipe Chat Assistant - Development Guide

## Quick Start

### Prerequisites
- Python 3.11+
- Google Cloud account (for Gemini API)
- Modal account (for deployment)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd recipe-chat-assistant
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Install package in development mode
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your credentials:
   # - JWT_SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
   # - GOOGLE_API_KEY (from https://ai.google.dev/aistudio)
   ```

5. **Run the development server**
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

6. **Access the application**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Detailed Health: http://localhost:8000/health/detailed

## Running Tests

### Run all tests
```bash
python run_tests.py
```

### Run specific test module
```bash
python run_tests.py auth          # Auth tests only
python run_tests.py recipes       # Recipe tests only
python run_tests.py websocket     # WebSocket tests only
```

### Run with coverage
```bash
python run_tests.py --coverage
```

### Run with pytest directly
```bash
pytest -v                         # Verbose output
pytest tests/test_auth.py         # Specific file
pytest -k "test_signup"           # Tests matching pattern
```

## Project Structure

```
recipe-chat-assistant/
├── src/
│   ├── api/              # API route handlers
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── recipes.py    # Recipe CRUD endpoints
│   │   └── chat.py       # WebSocket chat endpoint
│   ├── auth/             # Authentication logic
│   │   ├── security.py   # JWT and password handling
│   │   └── dependencies.py # FastAPI auth dependencies
│   ├── chat/             # WebSocket chat handling
│   │   └── websocket.py  # WebSocket message processing
│   ├── db/               # Database layer
│   │   ├── database.py   # Database connection
│   │   └── models.py     # SQLAlchemy models
│   ├── llm/              # LLM integration
│   │   ├── client.py     # Gemini client setup
│   │   └── recipe_processor.py # Recipe processing
│   ├── middleware/       # Custom middleware
│   │   └── rate_limit.py # Rate limiting
│   ├── models/           # Pydantic schemas
│   │   └── schemas.py    # Request/response models
│   ├── utils/            # Utility functions
│   │   └── validation.py # Input sanitization
│   ├── config.py         # Application configuration
│   └── main.py           # FastAPI application
├── tests/                # Test suite
├── prompts/              # LLM prompt templates
├── specs/                # API specifications
└── modal_app.py          # Modal deployment config
```

## API Endpoints

### Authentication
- `POST /v1/auth/signup` - Create new account
- `POST /v1/auth/signin` - Login with email/password
- `POST /v1/auth/refresh` - Refresh access token
- `POST /v1/auth/logout` - Invalidate refresh token
- `POST /v1/auth/forgot-password` - Request password reset
- `POST /v1/auth/reset-password` - Reset password with token

### Recipes
- `POST /v1/recipes` - Create new recipe
- `GET /v1/recipes` - List user's recipes
- `GET /v1/recipes/{id}` - Get specific recipe
- `PATCH /v1/recipes/{id}` - Update recipe
- `DELETE /v1/recipes/{id}` - Delete recipe

### WebSocket Chat
- `WS /v1/chat/{recipe_id}` - Real-time recipe chat

## Key Features

### Rate Limiting
- Auth endpoints: 10 requests/minute
- API endpoints: 60 requests/minute  
- WebSocket: 30 messages/minute
- Headers include rate limit info

### Security
- JWT authentication with refresh tokens
- Password hashing with bcrypt (12 rounds)
- Input sanitization with bleach
- CORS configuration
- Request logging

### Database
- SQLite with async support (aiosqlite)
- Recipe data stored as JSON
- Automatic timestamps
- User isolation

### LLM Integration
- Google Gemini 2.5 Flash
- OpenAI-compatible client
- Recipe extraction, generation, modification
- Automatic JSON validation

## Common Tasks

### Add a new API endpoint

1. Create route handler in `src/api/`
2. Add Pydantic schemas in `src/models/schemas.py`
3. Register router in `src/main.py`
4. Write tests in `tests/`

### Modify database schema

1. Update models in `src/db/models.py`
2. Create migration (if using in production)
3. Update tests
4. Run `init_db()` to recreate tables

### Add new LLM functionality

1. Add processing function in `src/llm/recipe_processor.py`
2. Create prompt template in `prompts/`
3. Update WebSocket handler in `src/chat/websocket.py`
4. Add tests with mocked LLM responses

## Debugging

### Enable debug mode
```bash
export DEBUG=true
uvicorn src.main:app --reload --log-level debug
```

### Check logs
- Request/response logging enabled
- Process time in headers
- Detailed error messages in debug mode

### Common issues

1. **Database errors**
   - Check DATABASE_URL is set correctly
   - Ensure .venv has write permissions for SQLite
   - Run with fresh database: `rm local_dev.db`

2. **LLM errors**
   - Verify GOOGLE_API_KEY is valid
   - Check rate limits (2 RPM for free tier)
   - Mock LLM calls in tests

3. **WebSocket issues**
   - Include JWT token in headers or query params
   - Check browser console for connection errors
   - Verify recipe ownership

## Deployment

### Modal Deployment

1. **Install Modal CLI**
   ```bash
   pip install modal
   modal token new
   ```

2. **Create secrets**
   ```bash
   modal secret create recipe-chat-secrets \
     JWT_SECRET_KEY=your-secret \
     GOOGLE_API_KEY=your-key \
     GOOGLE_OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   ```

3. **Deploy application**
   ```bash
   modal deploy modal_app.py
   ```

4. **Initialize database**
   ```bash
   modal run modal_app.py::init_deployment
   ```

5. **Check deployment**
   - Visit: https://your-app--fastapi-app.modal.run/health

### Environment Variables

Required for production:
- `JWT_SECRET_KEY` - Strong random secret
- `GOOGLE_API_KEY` - Gemini API key
- `DATABASE_URL` - Set automatically by Modal

Optional:
- `CORS_ORIGINS` - Comma-separated allowed origins
- `DEBUG` - Set to "false" in production
- SMTP settings for email (future)

## Contributing

1. Create feature branch
2. Write tests first (TDD)
3. Implement feature
4. Run tests and linting
5. Update documentation
6. Submit pull request

### Code Style
- Black for formatting
- isort for imports
- Type hints required
- Docstrings for public functions

### Testing Requirements
- All endpoints must have tests
- Mock external services (LLM, email)
- Test error scenarios
- Maintain >80% coverage

## License

See LICENSE file in repository root.