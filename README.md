# Recipe Chat Assistant

A chat-first recipe creation and management application built with FastAPI, WebSockets, and LLM integration. Extract recipes from text, generate recipes from natural language descriptions, and refine recipes through conversational AI.

## Features

- **Chat-First Recipe Creation**: Extract recipes from pasted text or generate from natural language descriptions
- **Real-Time Recipe Editing**: WebSocket-powered chat interface with live recipe preview
- **AI-Powered Assistant**: Integrated with Google Gemini 2.5 Pro for intelligent recipe processing
- **User Authentication**: JWT-based authentication with Auth0 integration
- **Flexible Storage**: JSONB recipe storage in PostgreSQL for easy schema evolution
- **Cross-Platform Database**: Compatible with both PostgreSQL and SQLite

## Prerequisites

- Python 3.11+
- [Auth0 account](https://auth0.com) (for authentication)
- [Google API key](https://ai.google.dev/aistudio) (for Gemini 2.5 Pro)

## Setup

### 1. Clone and Set Up Virtual Environment

```bash
# Clone the repository
git clone <repository-url>
cd meal_planner_claude_code_vibes

# Create project virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

Required credentials:
- **JWT_SECRET_KEY**: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- **AUTH0_DOMAIN**: Your Auth0 tenant domain (e.g., `dev-abc123.us.auth0.com`)
- **AUTH0_CLIENT_ID**: Your Auth0 application client ID
- **AUTH0_CLIENT_SECRET**: Your Auth0 application client secret
- **GOOGLE_API_KEY**: Get from [Google AI Studio](https://ai.google.dev/aistudio)

**Database Configuration:**
- **Local Development**: Uses SQLite (`./local.db`)
- **Production**: Uses SQLite on Modal Volume (automatically configured)

### 3. Frontend Setup

```bash
# Install frontend dependencies
cd frontend
npm install

# Configure frontend environment
cp .env.example .env
# Edit .env to point to your API (Modal or localhost)

# Run frontend in development mode
npm run dev
# Frontend will be available at http://localhost:3000

# Build frontend for production
npm run build
```

### 4. Local Development

```bash
# Run API locally with hot reload
python modal_app.py

# Run tests
pytest tests/

# API will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
# Frontend (if built) served from http://localhost:8000/
```

## Deployment to Modal

### 1. Create Modal Account and Install CLI

```bash
# Install Modal (if not already in requirements.txt)
pip install modal

# Authenticate with Modal
modal setup
```

### 2. Create Modal Secrets

```bash
# Create Modal secret from your .env file
python setup_modal_secrets.py
```

### 3. Deploy

```bash
# Deploy to Modal
python deploy.py

# Or deploy directly
modal deploy modal_app.py
```

Your app will be available at:
- **Production**: `https://gsganden--recipe-chat-assistant-fastapi-app.modal.run`
- **Development**: `https://gsganden--recipe-chat-assistant-fastapi-app-dev.modal.run`

## API Endpoints

- `GET /health` - Health check
- `POST /v1/auth/login` - User authentication
- `GET /v1/recipes` - List user recipes
- `POST /v1/recipes` - Create new recipe
- `WebSocket /v1/chat/{recipe_id}` - Real-time recipe chat

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: SQLite on Modal Volume (production) / SQLite (development)
- **Authentication**: JWT with Auth0
- **LLM Integration**: Google Gemini 2.5 Pro via OpenAI-compatible API
- **Real-time**: WebSockets
- **Deployment**: Modal

Created with Claude Code
