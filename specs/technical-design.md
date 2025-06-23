# Personal Recipe Book – Technical Design (v0.5)

> **Scope**: Ultra-minimal single‑user app focused on **chat-first recipe creation** through **LLM chat + live preview**. Extract from text, generate from prompts, or refine existing recipes.

---

## 1  Purpose & MVP Goals

* **Create** recipes via chat - extract from pasted text or generate from natural language requests.
* **Refine** each recipe through chat with an assistant, with direct field edits.
* **Store** recipes in chronological list with JSON backup.

## 2  Functional Requirements

| ID | Requirement                                                               |
| -- | ------------------------------------------------------------------------- |
| F1 | **Auth** – email/OAuth sign‑in (single tenant for now).                   |
| F2 | **Chat Recipe Creation** – extract from text or generate from prompts.     |
| F3 | **Chat‑Driven Editing** – two‑pane interface: chat + live recipe preview. |
| F4 | **Direct Field Editing** – user edits any field; syncs into chat context. |
| F5 | **Simple Storage** – recipes stored chronologically, no versioning.       |
| F6 | **JSON Backup** – export all recipes as JSON for backup.                  |

## 3  Non‑Functional Requirements

* **Latency** – p95 <200 ms read, <400 ms write.
* **Offline** – IndexedDB cache for viewing & editing without network.
* **Security** – data encrypted at rest (AES‑256 Postgres) and in transit (HTTPS).
* **Accessibility** – WCAG 2.1 AA.

## 4  High‑Level Architecture

```
(Client SPA / React Native)
        ▲ WebSocket (chat) / HTTPS (REST)
        │
        ▼
 Recipe API (FastAPI) ──────────▶ PostgreSQL (Neon/Supabase)
        │                              ▲
        │ chat messages                 │ recipe CRUD
        ▼                              │
 LLM Router (@modal.function) ─────────┘
        │
        ▼
 OpenAI/Anthropic APIs
```

* **Recipe API** – FastAPI app exposed via `@modal.asgi()` handling auth, CRUD, and WebSocket chat.
* **LLM Router** – processes chat messages for recipe extraction/generation; cached model weights on Modal volumes.
* **No async workers** – all operations happen synchronously within chat flow.

## 5  Data Model (Core Tables)

| Table             | Key Columns                                                          |
| ----------------- | -------------------------------------------------------------------- |
| `users`           | id, email, name, created\_at                                         |
| `recipes`         | id, owner\_id, recipe\_data (JSONB), created\_at, updated\_at       |

**Key Design Decision**: Recipes are stored as JSONB documents in `recipes.recipe_data`, containing the full recipe JSON as defined in `recipe-schema.json`. This provides:
- Direct mapping between API and storage layers
- Simple updates (no versioning)
- Fast single-query reads
- JSON path indexing for future search

## 6  Chat-Based Recipe Creation

1. **User Input** – paste text or describe recipe needs via WebSocket chat.
2. **LLM Processing** – extract structured recipe from text OR generate from description.
3. **Validation** – ensure output matches recipe JSON schema.
4. **Live Preview** – stream recipe updates to client via WebSocket.
5. **Persist** – save final recipe JSON to database when user confirms.

## 7  Chat‑Driven Recipe Builder – UI/UX

* Left chat, right live recipe form.
* Direct edits emit system messages so LLM stays in sync.
* Quick actions (rewrite, convert units, substitutions) call backend LLM endpoints.
* Autosave (debounce 2 s); explicit **Save** → update recipe.

## 8  LLM Processing Strategy (Modal)

* **Synchronous Invocation** – `modal.Function.remote()` for chat messages; real-time responses.
* **Concurrency Limits** – set per function (`concurrency_limit=10`); CPU tier for most models.
* **Retries** – Modal built‑in retries; graceful fallback for LLM failures in chat.

## 9  Deployment & DevOps on Modal

| Stage             | Action                                                                                                       |
| ----------------- | ------------------------------------------------------------------------------------------------------------ |
| **CI**            | GitHub Actions pushes → `modal deploy recipe_app.py` builds & publishes image.                               |
| **Staging Test**  | `modal run smoke_tests.py` against staging Postgres.                                                         |
| **Prod Release**  | Promote tagged image; Modal routes traffic to new version (blue‑green).                                      |
| **Observability** | Modal dashboard logs & latency; custom Prom metrics → Grafana Cloud via remote write; Sentry for exceptions. |
| **Secrets**       | `modal.Secret.from_dict()` injects OpenAI keys, DB URL.                                                      |

## 10  LLM Usage Patterns

| Use Case              | Prompt template                                 | Response         |
| --------------------- | ----------------------------------------------- | ---------------- |
| Extract recipe        | "Extract a recipe from this text in JSON schema…" | Full recipe JSON |
| Generate recipe       | "Create a recipe for {description} that meets {constraints}…" | Full recipe JSON |
| Ingredient substitute | "Suggest 3 dairy‑free replacements for butter…" | Bullet list      |
| Rewrite step          | "Rewrite this step at 8th‑grade level…"         | String           |
| Scale recipe          | "Adjust this recipe to serve {servings} people…" | Updated JSON     |

## 11  Future (Post‑MVP)

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