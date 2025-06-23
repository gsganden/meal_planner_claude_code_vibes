# Import Pipeline – I/O Spec (v0.1)

> **Purpose:** Define the exact data shapes exchanged between the API layer, the Modal import worker, and downstream consumers so that multiple developers can work on pieces independently without integration churn.

---

## 1. Lifecycle Diagram

```
Client ──POST /v1/import──────────────▶ API
        ◀─202 + job_id────────────────
                                     │  INSERT import_jobs row (status=queued)
                                     ▼
                           Modal Function (import_worker)
                                     │  FETCH job by id
                                     │  status → running
   (progress webhooks)  ◀────────────┤  UPDATE progress, logs
                                     │
                                     │  On success:
                                     │    • Extract recipe_json
                                     │    • INSERT recipes + recipe_versions rows
                                     │    • status → completed, recipe_id=…
                                     │  On failure:
                                     │    • status → failed, error_* cols
                                     ▼
Client ──GET /v1/import/{job_id}──────▶ API (poll) ─▶ DB
```

## 2. API Payloads

### 2.1 Start Import

**Request** `POST /v1/import`

```json5
{
  "source_type": "url",          // enum: url|pdf|image|video|text
  "source_ref": "https://foo.bar/recipe.html"  // URL or file token
}
```

**Response** `202 Accepted`

```json
{ "id": "<job_id>", "status": "queued" }
```

### 2.2 Poll Status

`GET /v1/import/{job_id}` → `200 OK`

```json5
{
  "id": "f3db…",
  "status": "completed",        // queued|running|failed|completed
  "progress": 100,              // 0‑100 integer
  "recipe_id": "18a0…",        // present when completed
  "error_code": null,
  "error_msg": null,
  "updated_at": "2025-06-23T18:44:00Z"
}
```

> For `failed`, `error_code` MUST be non‑null (see §4).

---

## 3. Database Schema – `import_jobs`

| Column       | Type        | Notes                                     |
| ------------ | ----------- | ----------------------------------------- |
| id           | UUID PK     | Generated in API layer                    |
| user\_id     | UUID FK     | Owner of the job                          |
| source\_type | text        | url/pdf/image/video/text                  |
| source\_ref  | text        | URL or file token from upload API          |
| source\_hash | char(64)    | SHA‑256 of raw content for idempotency    |
| status       | text        | queued/running/failed/completed           |
| progress     | int         | 0‑100                                     |
| recipe\_id   | UUID FK     | Set on success                            |
| error\_code  | text        | machine‑readable (see §4)                 |
| error\_msg   | text        | human message (<=256 chars)               |
| created\_at  | timestamptz | default now()                             |
| started\_at  | timestamptz | nullable                                  |
| finished\_at | timestamptz | nullable                                  |
| updated\_at  | timestamptz | auto‑update trigger                       |

**Unique Constraint** `(user_id, source_hash)` WHERE status != 'failed'\` — prevents duplicate imports of identical content unless previous attempt failed.

---

## 4. Error Codes

| Code                 | Meaning & mitigation                                                              |
| -------------------- | --------------------------------------------------------------------------------- |
| `download_error`     | HTTP fetch failed / timeout. Retry allowed.                                       |
| `unsupported_format` | File type not recognized. Show user message.                                      |
| `extraction_failed`  | Schema.org + rule‑based parse both failed and LLM fallback returned invalid JSON. |
| `timeout`            | Worker exceeded 600 s soft limit. Suggest user try again later.                   |
| `oom`                | Worker out of memory (large PDF/video).                                           |

---

## 5. Worker Function Signatures

```python
@modal.function(concurrency_limit=4, timeout=600)
async def import_worker(job_id: str):
    job = db.fetch_import_job(job_id)
    job.status = "running"
    db.save(job)

    try:
        progress(5)
        raw = ingest(job)
        progress(25)
        cleaned = preprocess(raw)
        progress(50)
        recipe_json = extract_recipe(cleaned)  # may call LLM
        progress(90)
        recipe_id = persist_recipe(job.user_id, recipe_json)
        job.status = "completed"
        job.recipe_id = recipe_id
    except ImportError as exc:
        job.status = "failed"
        job.error_code = exc.code
        job.error_msg = str(exc)
    finally:
        job.progress = 100
        db.save(job)
```

*`progress(x)` helper updates `import_jobs.progress` and `updated_at`; API poller can surface to client.*

---

## 6. Progress Update Events (Optional WebSocket)

If live progress is desired:

```json
{
  "type": "import_progress",
  "job_id": "f3db…",
  "progress": 65,
  "status": "running"
}
```

Published via Redis pub/sub; the WebSocket `/v1/chat/{recipeId}` can multiplex import updates.

---

## 7. Idempotency Workflow

1. API calculates `source_hash` (SHA‑256) from URL contents or file bytes.
2. Check existing row with same `(user_id, source_hash)` where status IN (queued,running,completed).
3. If found → return existing `job_id` & status (HTTP 200).
4. Else → create new job.

---

## 8. SLA Targets

| Metric                                 | Target                         |
| -------------------------------------- | ------------------------------ |
| 90th‑pct job latency (URL, <2 MB HTML) | <20 s                          |
| 90th‑pct job latency (PDF 5 MB)        | <60 s                          |
| Failed job rate                        | <3 % rolling 7‑day             |
| Duplicate prevention hit rate          | >95 % identical URL re‑submits |

---

*End of I/O Spec v0.1*