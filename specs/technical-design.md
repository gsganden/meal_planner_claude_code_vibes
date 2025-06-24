# Recipe Chat Assistant – Technical Design (v0.5)

> **Scope**: Ultra-minimal single‑user app focused on **chat-first recipe creation** through **LLM chat + live preview**. Extract from text, generate from prompts, or refine existing recipes.

---

## 1  Purpose & MVP Goals

* **Create** recipes via chat - extract from pasted text or generate from natural language requests.
* **Refine** each recipe through chat with an assistant, with direct field edits.
* **Store** recipes in chronological list with JSON backup.

## 2  Functional Requirements

| ID | Requirement                                                               |
| -- | ------------------------------------------------------------------------- |
| F1 | **Auth** – traditional email/password authentication with signup and signin flows. |
| F2 | **Chat Recipe Creation** – extract from text or generate from prompts.     |
| F3 | **Chat‑Driven Editing** – two‑pane interface: chat + live recipe preview. |
| F4 | **Direct Field Editing** – user edits any field; syncs into chat context. |
| F5 | **Simple Storage** – recipes stored chronologically, no versioning.       |
| F6 | **JSON Backup** – export all recipes as JSON for backup.                  |

## 3  Non‑Functional Requirements

* **Latency** – p95 <200 ms read, <400 ms write.
* **Offline** – IndexedDB cache for viewing & editing without network.
* **Security** – data encrypted at rest (SQLite on Modal Volume) and in transit (HTTPS).
* **Accessibility** – WCAG 2.1 AA.

## 4  High‑Level Architecture

```
(Client SPA / React Native)
        ▲ WebSocket (chat) / HTTPS (REST)
        │
        ▼
 Recipe API (FastAPI) ──────────▶ SQLite on Modal Volume
        │                              ▲
        │ chat messages                 │ recipe CRUD
        ▼                              │
 LLM Router (@modal.function) ─────────┘
        │
        ▼
 Google Gemini API
```

* **Recipe API** – FastAPI app exposed via `@modal.asgi()` handling auth, CRUD, and WebSocket chat.
* **LLM Router** – processes chat messages for recipe extraction/generation; cached model weights on Modal volumes.
* **No async workers** – all operations happen synchronously within chat flow.

## 5  Data Model (Core Tables)

| Table             | Key Columns                                                          |
| ----------------- | -------------------------------------------------------------------- |
| `users`           | id, email, password\_hash, name, created\_at                        |
| `recipes`         | id, owner\_id, recipe\_data (JSONB), created\_at, updated\_at       |

**Key Design Decision**: Recipes are stored as JSONB documents in `recipes.recipe_data`, containing the full recipe JSON as defined in `recipe-schema.json`. This provides:
- Direct mapping between API and storage layers
- Simple updates (no versioning)
- Fast single-query reads
- JSON path indexing for future search

**Recipe Validation**: Recipes require only a title (minimum "Untitled Recipe {N}"). Ingredients and steps arrays can be empty to support incremental recipe building and immediate saving upon creation.

### 5.1  Authentication Architecture

**Authentication Method**: Traditional email/password with JWT tokens

**User Registration & Login Flow**:
1. **Sign Up**: User provides email + password → system creates account with hashed password
2. **Sign In**: User provides email + password → system validates against stored hash
3. **JWT Tokens**: Successful authentication returns access + refresh token pair
4. **Session Management**: Frontend stores tokens in localStorage, includes in API requests

**Password Requirements**:
- Minimum 8 characters
- Must contain at least one letter and one number
- Hashed using bcrypt with salt rounds ≥12

**API Endpoints**:
- `POST /v1/auth/signup` – Create new account (email, password, confirmPassword) → 201 Created
- `POST /v1/auth/signin` – Authenticate existing user (email, password) → 200 OK
- `POST /v1/auth/refresh` – Refresh access token using refresh token → 200 OK  
- `POST /v1/auth/logout` – Invalidate refresh token → 200 OK
- `POST /v1/auth/forgot-password` – Send password reset email (email) → 200 OK
- `POST /v1/auth/reset-password` – Reset password with token (token, newPassword) → 200 OK

**Frontend Authentication State Management**:
- **Global Auth State**: Centralized authentication state with listener pattern
- **Reactive Updates**: All components using `useAuth()` hook automatically re-render on auth changes
- **State Persistence**: JWT tokens stored in localStorage, automatically loaded on app startup
- **Immediate Transitions**: Authentication success triggers immediate UI updates without manual navigation

**Authentication State Properties**:
```typescript
interface AuthState {
  isAuthenticated: boolean  // Whether user has valid session
  isLoading: boolean       // During app startup auth check
  user: User | null        // User profile data (optional)
}
```

**Authentication Flow Architecture**:
1. **App Initialization**: Check localStorage for existing token → set loading state → update auth state
2. **Login Success**: Save token → notify all listeners → automatic redirect to main app
3. **Logout**: Clear token → notify all listeners → automatic redirect to login page
4. **Token Expiration**: Automatic redirect to login with session expired message

**Frontend Form Validation Requirements**:
- **Real-time Validation**: Email format validation on blur, password confirmation matching during typing
- **Submit Button State**: Disabled until all validations pass, visual feedback (gray→blue)
- **Loading States**: Button text changes during submission, form disabled during requests
- **Form State Persistence**: Email retained when switching modes, passwords clear for security
- **Error Display**: Immediate error messages above form, clear on mode switch or field modification

**Security Considerations**:
- Passwords never stored in plain text
- JWT tokens signed with strong secret key  
- Refresh tokens have longer expiration than access tokens
- No password enumeration attacks (consistent error messages)
- Client-side validation backed by server-side validation
- Secure password requirements enforced on both frontend and backend

**Error Handling & User Experience**:
- **User-Friendly Messages**: All API errors converted to human-readable messages (never show raw JSON to users)
- **Consistent Error Format**: Frontend displays errors in consistent UI components (red banners, inline field errors)
- **Authentication Errors**: 
  - Invalid credentials: "Invalid email or password"
  - Account not found: "Invalid email or password" (no email enumeration)
  - Rate limiting: "Too many attempts. Please wait before trying again."
  - Network errors: "Unable to connect. Please check your connection and try again."
- **Password Reset Flow**: "Forgot password?" link on signin form → email input → "Check your email for reset instructions"

## 6  Chat-Based Recipe Creation

1. **User Input** – paste text or describe recipe needs via WebSocket chat.
2. **LLM Processing** – extract structured recipe from text OR generate from description.
3. **Validation** – ensure output matches recipe JSON schema.
4. **Live Preview** – stream recipe updates to client via WebSocket.
5. **Persist** – save final recipe JSON to database when user confirms.

## 7  User Interface & Navigation

### 7.1  Application Entry & Navigation
* **Home Page** – Recipe list showing titles, descriptions, creation dates in reverse chronological order
* **New Recipe Button** – Prominent action to start fresh recipe creation
* **Recipe Selection** – Click any recipe to open in editor mode
* **Navigation** – Clear back/home navigation from editor to recipe list

### 7.2  Recipe Creation Flow (New Recipe)
* **Immediate Creation** – Recipe created immediately with auto-generated title "Untitled Recipe {N}" (auto-incrementing number)
* **Initial State** – Recipe form shows auto-title, empty ingredients array, empty steps array, chat prompt: "How can I help you create a recipe?"
* **WebSocket Connection** – Connects immediately using real recipe ID from database
* **Autosave** – Begins immediately as user types in form fields or interacts via chat
* **URL** – Shows `/recipe/{id}` from the start (no URL transitions needed)

### 7.3  Recipe Editing Flow (Existing Recipe)
* **Load State** – Recipe data populates form, chat history loads previous conversation
* **Chat Context** – User sees previous assistant interactions for this recipe
* **Continuation** – User can continue previous conversation or start new topics

### 7.4  Chat‑Driven Recipe Builder
* **Layout** – Left chat pane (40%), right live recipe form (60%)
* **Real-time Updates** – Recipe form updates immediately as LLM streams responses
* **Direct Edit Integration** – Form edits emit system messages: "User updated [field]: [old] → [new]"
* **Chat History** – Scrollable conversation preserved per recipe

### 7.5  Save States & User Feedback
* **Autosave Indicator** – "Saving..." during 2-second debounce, "Saved" when complete
* **Unsaved Changes** – Yellow border/indicator on modified fields before autosave
* **Explicit Save** – Green "Save Recipe" button for user-initiated saves
* **Save Failures** – Red error message with retry option

### 7.6  Quick Actions Interface
* **Location** – Toolbar above recipe form with contextual buttons
* **Actions Available**:
  - "Rewrite" (for any text field) → sends "Please rewrite this [field] to be clearer"
  - "Convert Units" → sends "Convert ingredients to metric/imperial" 
  - "Make Substitutions" → sends "Suggest ingredient substitutions for dietary needs"
* **Behavior** – Clicking sends predefined message to chat, shows loading state

### 7.7  Error States & Recovery
* **Connection Lost** – Red banner: "Connection lost. Reconnecting..." with manual retry
* **LLM Timeout** – Chat message: "Sorry, that took too long. Please try again."
* **Invalid Data** – Form field highlights with error message, prevents save
* **Auth Expiration** – Redirect to login with "Session expired" message

## 8  LLM Integration Architecture

### 8.1  Gemini API via OpenAI-Compatible Interface

**Service Provider:** Google Gemini 2.5 Flash via Google's official OpenAI-compatible API  
**Documentation:** https://ai.google.dev/gemini-api/docs/openai  
**Endpoint:** `https://generativelanguage.googleapis.com/v1beta/openai/`

**Key Design Decision:** Use Google's official OpenAI-compatible interface to access Gemini models while maintaining standard OpenAI Python library code patterns.

**Benefits:**
- Official Google support (no third-party wrapper services)
- Keep existing OpenAI library code unchanged
- Direct billing with Google
- Full access to Gemini model capabilities
- Consistent with team's OpenAI experience

### 8.2  Environment Configuration

```bash
# Required Environment Variables
GOOGLE_API_KEY="your-google-api-key"                                          # From ai.google.dev
GOOGLE_OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"  # Google's OpenAI endpoint
```

**API Key Setup:**
1. Visit https://ai.google.dev/aistudio
2. Create/sign in to Google account
3. Generate API key for Gemini API
4. Use this key as `GOOGLE_API_KEY` (NOT an OpenAI key)

### 8.3  Model Configuration

**Primary Model:** `gemini-2.5-flash` (Google's fast, efficient model)  
**Fallback Model:** `gemini-1.5-pro` (stable production)

**LLM Registry Configuration:**
```yaml
models:
  default:
    model: "gemini-2.5-flash"
    settings:
      temperature: 0.1
      max_tokens: 2048
  fast:
    model: "gemini-2.5-flash"
    settings:
      temperature: 0.2
      max_tokens: 1024
```

### 8.4  Implementation Pattern

```python
import openai

client = openai.OpenAI(
    api_key=os.environ["GOOGLE_API_KEY"],        # Google API key, not OpenAI
    base_url=os.environ["GOOGLE_OPENAI_BASE_URL"] # Google's OpenAI-compatible endpoint
)

response = client.chat.completions.create(
    model="gemini-2.5-flash",
    messages=[{"role": "user", "content": "Extract recipe from: ..."}]
)
```

### 8.5  Prompt Library Integration

**Prompt Templates:** Stored in `prompts/` directory as YAML files  
**Template Engine:** Jinja2 for variable substitution  
**Fallback Strategy:** Hardcoded prompts if template files unavailable

**Example Prompt Structure:**
```yaml
# prompts/recipe_extract.yaml
name: "recipe_extract"
version: "v1"
template: |
  Extract a recipe from the following text and return it as JSON matching this schema:
  {{ schema }}
  
  Text to extract from:
  {{ text }}
  
  Return only valid JSON, no other text.
```

## 9  LLM Processing Strategy (Modal)

* **Synchronous Invocation** – `modal.Function.remote()` for chat messages; real-time responses.
* **Concurrency Limits** – set per function (`concurrency_limit=10`); CPU tier for most models.
* **Retries** – Modal built‑in retries; graceful fallback for LLM failures in chat.

## 9  Deployment & DevOps on Modal

### 9.1  Modal App Configuration

**App Name:** `recipe-chat-assistant`  
**Database:** SQLite on Modal Volume for persistent storage  
**Volume:** `recipe-data-volume` mounted at `/data` for database persistence  
**Secrets:** `recipe-chat-secrets` containing all environment variables

### 9.2  Required Environment Variables (Modal Secrets)

```bash
# Authentication
JWT_SECRET_KEY="secure-random-string"           # For JWT token signing (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")

# LLM Integration (Google Gemini)
GOOGLE_API_KEY="your-google-api-key"                                          # From ai.google.dev
GOOGLE_OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"  # Google's OpenAI endpoint

# Database (Automatically configured)
# DATABASE_URL="sqlite+aiosqlite:///data/production.db"                       # Set automatically by app

# Application (Optional - have defaults)
APP_NAME="Recipe Chat Assistant"
DEBUG="false"
CORS_ORIGINS="https://recipe-chat-assistant.vercel.app,http://localhost:3000"
```

### 9.3  Deployment Pipeline

| Stage             | Action                                                                                                       |
| ----------------- | ------------------------------------------------------------------------------------------------------------ |
| **Setup**         | `modal secret create recipe-chat-secrets` with all required environment variables                            |
| **Volume**        | `modal volume create recipe-data-volume` creates persistent storage for SQLite database                     |
| **Deploy**        | `modal deploy modal_app.py` builds image, creates volume, and deploys FastAPI app                          |
| **Initialize**    | `modal run modal_app.py::init_deployment` creates SQLite database tables on volume                         |
| **Verify**        | Test `/health` endpoint at `https://recipe-chat-assistant--fastapi-app.modal.run/health`                   |
| **Monitor**       | Modal dashboard for logs, metrics, and scaling                                                              |

### 9.4  System Configuration Requirements

**Environment Configuration:**
The application requires these environment variables for proper operation:
- **`GOOGLE_API_KEY`**: Google API key for Gemini model access
- **`GOOGLE_OPENAI_BASE_URL`**: Google's OpenAI-compatible endpoint URL
- **`JWT_SECRET_KEY`**: Secure random string for JWT token signing
- **`DATABASE_URL`**: SQLite database path on Modal volume (`/data/production.db`)

**LLM Integration:**
- Application uses Google Gemini 2.5 Flash via OpenAI-compatible interface
- Model client authenticates with Google API key (not OpenAI key)
- Default model configured as `gemini-2.5-flash` in model registry

**Storage Requirements:**
- Modal Volume mounted at `/data` for SQLite database persistence
- Database file located at `/data/production.db` on the mounted volume
- Volume provides durability and backup for all recipe and user data

**Deployment Validation:**
The deployed system should satisfy these functional requirements:
1. Health endpoint returns 200 OK status
2. User authentication flow works end-to-end
3. Recipe CRUD operations function correctly
4. WebSocket chat connections establish successfully
5. LLM integration processes recipe requests properly

## 10  Database Strategy: SQLite on Modal Volumes

### 10.1  Rationale

**Why SQLite for Production:**
- **Simplicity**: No external database setup, credentials, or connection management required
- **Self-contained**: All infrastructure stays within Modal platform
- **Cost-effective**: No separate database hosting costs
- **Performance**: Local filesystem access, no network latency for queries
- **Reliability**: Modal Volumes provide persistent, replicated storage

**Why Modal Volumes:**
- **Persistent Storage**: Data survives container restarts and deployments
- **Automatic Backups**: Modal handles volume replication and durability
- **Mount Simplicity**: Volume mounts seamlessly at specified paths
- **Scalability**: Can be shared across multiple containers if needed

### 10.2  Performance Characteristics

**Workload Suitability:**
- **Read-heavy**: Recipe browsing, chat history - excellent performance
- **Write-moderate**: Recipe creation/editing - sufficient for single-user MVP
- **Concurrent Users**: SQLite handles multiple readers, serialized writes
- **Data Size**: Recipes as JSONB - compact storage, efficient queries

**Performance Targets:**
- **Recipe Reads**: <50ms (local filesystem access)
- **Recipe Writes**: <200ms (including validation + JSONB processing)
- **Chat Messages**: <100ms (simple inserts with indexing)
- **Database Size**: ~100MB for 10,000 recipes with chat history

### 10.3  Scaling Considerations

**Current MVP Scale:**
- Single-user application
- Hundreds of recipes
- Moderate chat activity
- SQLite WAL mode for better concurrency

**Future Scaling Options:**
- **Read Replicas**: Mount volume read-only on additional containers
- **Backup Strategy**: Periodic SQLite backups to Modal storage
- **Migration Path**: Can export all JSONB data for PostgreSQL migration if needed
- **Monitoring**: Track database file size, query performance metrics

## 11  LLM Usage Patterns

| Use Case              | Prompt template                                 | Response         |
| --------------------- | ----------------------------------------------- | ---------------- |
| Extract recipe        | "Extract a recipe from this text in JSON schema…" | Full recipe JSON |
| Generate recipe       | "Create a recipe for {description} that meets {constraints}…" | Full recipe JSON |
| Ingredient substitute | "Suggest 3 dairy‑free replacements for butter…" | Bullet list      |
| Rewrite step          | "Rewrite this step at 8th‑grade level…"         | String           |
| Scale recipe          | "Adjust this recipe to serve {servings} people…" | Updated JSON     |

## 12  Future (Post‑MVP)

* File import (PDF, images, video).
* Search and filtering recipes.
* Recipe versioning and history.
* Export to various formats.
* Semantic search & vector DB.
* Grocery list & meal‑planning.
* Social sharing & collaboration.
* Voice‑guided cooking mode.

---

*End of v0.5*