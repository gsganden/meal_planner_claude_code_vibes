# Logging & Monitoring Spec (v0.1)

> **Goal:** Provide uniform observability across API, import worker, and LLM router functions while running on Modal and Postgres. This spec defines log structure, metrics, dashboards, and alert thresholds required for the MVP.

---

## 1. Logging

### 1.1 Format

* **JSON per line** (NDJSON) to stdout. Modal collects and surfaces logs in dashboard; Loki integration can scrape.

* **Field schema**:

  | Field       | Type            | Example                                  | Notes                          |
  | ----------- | --------------- | ---------------------------------------- | ------------------------------ |
  | `ts`        | RFC 3339 string | `2025-06-23T19:02:11.123Z`               | UTC only                       |
  | `level`     | string          | `INFO`, `WARN`, `ERROR`                  |                                |
  | `service`   | string          | `api` \| `import_worker` \| `llm_router` |                                |
  | `req_id`    | UUID            | `70af…`                                  | Correlates logs across modules |
  | `user_id`   | UUID            | `18a0…`                                  | Optional (null for unauth)     |
  | `recipe_id` | UUID            | `f3db…`                                  | Optional                       |
  | `job_id`    | UUID            | `c1b2…`                                  | For import jobs                |
  | `event`     | string          | `import_started`, `llm_call`, `db_query` |                                |
  | `msg`       | string          | Human message                            |                                |
  | `extra`     | object          | provider‑specific payload                | Free‑form JSON                 |

* **Library**: `structlog` configured with `structlog.processors.JSONRenderer()`.

### 1.2 Correlation IDs

* API entrypoint generates `req_id` (uuid4) per HTTP/WebSocket request and passes it via context var into worker spawns and LLM calls.
* Workers include original `req_id` plus their own `job_id`.

### 1.3 Log Levels & Sampling

* Default `INFO`. For `llm_call` logs (potentially noisy) apply 10 % sampling at `INFO`, else log `DEBUG`.
* Unexpected exceptions always `ERROR`.

---

## 2. Metrics

### 2.1 Collection Stack

* **Prometheus**: Modal supports remote‑write; export metrics via `prometheus_client`.
* **Grafana Cloud** dashboard template stored in `observability/grafana/recipe_dashboard.json`.

### 2.2 Metric List

| Metric                          | Type      | Labels                          | Description                |
| ------------------------------- | --------- | ------------------------------- | -------------------------- |
| `http_request_duration_seconds` | Histogram | `method`, `path`, `status`      | API latency                |
| `import_job_latency_seconds`    | Histogram | `source_type`, `status`         | End‑to‑end import time     |
| `import_job_failures_total`     | Counter   | `error_code`                    | Failed imports             |
| `llm_call_tokens_total`         | Counter   | `provider`, `model_ref`, `role` | Prompt + completion tokens |
| `llm_call_latency_seconds`      | Histogram | `provider`, `model_ref`         | LLM response time          |
| `db_query_seconds`              | Histogram | `operation`                     | SQL latency                |

Buckets: `[0.1, 0.3, 1, 3, 10, 30, 60, 120]` seconds.

### 2.3 Error Budget & SLIs

| SLI                                       | Target             |
| ----------------------------------------- | ------------------ |
| Import success rate (`completed / total`) | ≥ 97 % rolling 7 d |
| p95 API latency (`GET /v1/recipes/{id}`)  | < 200 ms           |
| p95 import latency (URL <2 MB)            | < 20 s             |

---

## 3. Alerting (Grafana Cloud)

| Alert                     | Condition                                                                | Severity | Action        |
| ------------------------- | ------------------------------------------------------------------------ | -------- | ------------- |
| **High API error rate**   | `5 min avg rate(http_request_total{status=~"5.."}) > 1/s`                | P1       | PagerDuty     |
| **Import failures spike** | `import_job_failures_total` increase > 50 in 15 min                      | P2       | Slack #alerts |
| **LLM latency**           | p95 `llm_call_latency_seconds` > 10 s for 5 min                          | P2       | Slack         |
| **DB slow queries**       | p95 `db_query_seconds{operation="INSERT import_jobs"} > 1 s` over 10 min | P3       | Slack         |

---

## 4. Dashboards

* **API Overview** – Requests/s, latency percentiles, error codes.
* **Import Pipeline** – Jobs by status, latency histogram, top error codes.
* **LLM Usage & Cost** – Token counters by provider/model, latency.
* **DB Performance** – TPS, slowest queries, connections.

Dashboard JSON lives under `observability/grafana/` and is imported on Grafana startup.

---

## 5. Implementation Checklist

* [ ] Install `structlog`, `prometheus_client` in `requirements.txt`.
* [ ] Configure `structlog` JSON renderer in `app.__init__`.
* [ ] Middleware to generate `req_id` and push to context var.
* [ ] Decorator `@metric_timer` to wrap key functions (import\_worker phases, LLM calls).
* [ ] `observability/README.md` with Grafana import instructions.

---

*End of Logging & Monitoring Spec v0.1*