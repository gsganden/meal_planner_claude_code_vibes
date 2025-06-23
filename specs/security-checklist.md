# Security Checklist – Personal Recipe Book (v0.1)

> **Scope:** Items must be satisfied before MVP launch. Aligns with OWASP Top‑10, CIS Benchmarks, and Modal's security model. Each item is tagged with **OWNER** (Dev, DevOps, Product) and **PHASE** (Dev, Code Review, Deploy, Post‑Deploy).

---

## 1. Authentication & Session Security

| #   | Checklist Item                                                                                                           | Owner  | Phase  |
| --- | ------------------------------------------------------------------------------------------------------------------------ | ------ | ------ |
| 1.1 | OAuth & magic‑link flows require **PKCE** (if public client) or signed JWT redirect URIs.                                | Dev    | Dev    |
| 1.2 | JWT access tokens ≤15 min; refresh ≤7 days; **rotate refresh ID** on use.                                                | Dev    | Dev    |
| 1.3 | Token secrets (JWT signing key) stored only in Modal secret **`recipe_secrets`**; never in code or env committed to VCS. | DevOps | Deploy |

## 2. Authorization

| #   | Checklist Item                                                                                      | Owner | Phase |
| --- | --------------------------------------------------------------------------------------------------- | ----- | ----- |
| 2.1 | All DB queries filter by `user_id`; no cross‑tenant access. Unit test coverage for "leakage" cases. | Dev   | Dev   |
| 2.2 | Import status polling (`/v1/import/{id}`) checks job's `user_id` matches auth identity.             | Dev   | Dev   |

## 3. Data Protection & Privacy

| #   | Checklist Item                                                                   | Owner   | Phase       |
| --- | -------------------------------------------------------------------------------- | ------- | ----------- |
| 3.1 | **AES‑256‑GCM** at‑rest encryption enabled for Postgres (Neon/Supabase default). | DevOps  | Deploy      |
| 3.2 | All backups encrypted with server‑side encryption and stored in private bucket.  | DevOps  | Post‑Deploy |
| 3.3 | PII limited to email; no ingredient or recipe data considered sensitive.         | Product | Review      |

## 4. Network & Transport

| #   | Checklist Item                                                                                                                                       | Owner  | Phase  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------ |
| 4.1 | Force HTTPS for all endpoints (`Strict‑Transport‑Security: max‑age 63072000; includeSubDomains`).                                                    | DevOps | Deploy |
| 4.2 | Set secure headers via FastAPI `SecureHeadersMiddleware`: `Content‑Security‑Policy`, `X‑Frame‑Options`, `Referrer‑Policy`, `X‑Content‑Type‑Options`. | Dev    | Dev    |

## 5. Input Validation & Sanitization

| #   | Checklist Item                                                                 | Owner | Phase |
| --- | ------------------------------------------------------------------------------ | ----- | ----- |
| 5.1 | All API payloads validated by Pydantic models or `pydantic‑core` before use.   | Dev   | Dev   |
| 5.2 | LLM JSON output validated against `recipe_schema.json`; reject parsing errors. | Dev   | Dev   |
| 5.3 | File uploads (PDF, image) scan mime type magic bytes & size ≤25 MB.            | Dev   | Dev   |

## 6. Dependency & Supply‑Chain Security

| #   | Checklist Item                                                                       | Owner  | Phase  |
| --- | ------------------------------------------------------------------------------------ | ------ | ------ |
| 6.1 | Enable **Dependabot** and GitHub Advisory scanning; block PR merge on critical CVEs. | DevOps | Dev    |
| 6.2 | `requirements.txt` pinned (`==`) and signed with `pip‑compile`.                      | Dev    | Dev    |
| 6.3 | Use `pip install --require-hashes` in Modal image build to prevent tampering.        | DevOps | Deploy |

## 7. Secrets Management

| #   | Checklist Item                                                                    | Owner  | Phase       |
| --- | --------------------------------------------------------------------------------- | ------ | ----------- |
| 7.1 | All secrets injected via `modal.Secret` object; no `os.environ` defaults in code. | DevOps | Deploy      |
| 7.2 | Rotate `OPENAI_API_KEY`, DB passwords every 90 days; document rotation SOP.       | DevOps | Post‑Deploy |

## 8. Rate Limiting & Abuse Prevention

| #   | Checklist Item                                                                | Owner | Phase |
| --- | ----------------------------------------------------------------------------- | ----- | ----- |
| 8.1 | Global rate limit: 300 requests/min/IP via FastAPI Limiter or gateway config. | Dev   | Dev   |
| 8.2 | Import start endpoint limited to 20 jobs/min/user.                            | Dev   | Dev   |

## 9. Logging & Monitoring Security

| #   | Checklist Item                                            | Owner  | Phase       |
| --- | --------------------------------------------------------- | ------ | ----------- |
| 9.1 | Ensure no keys or PII in logs (`extra` fields scrubbed).  | Dev    | Dev         |
| 9.2 | Alert on >10 auth failures/min/IP (possible brute force). | DevOps | Post‑Deploy |

## 10. Incident Response & Backup

| #    | Checklist Item                                                                      | Owner  | Phase       |
| ---- | ----------------------------------------------------------------------------------- | ------ | ----------- |
| 10.1 | Automated daily db backup; tested restore script quarterly.                         | DevOps | Post‑Deploy |
| 10.2 | Maintain **Runbook.md** with steps for import pipeline outage, LLM provider outage. | DevOps | Post‑Deploy |

---

*End of Security Checklist v0.1*