# Logging & Monitoring Spec (v0.1)

> **Goal:** Provide uniform observability across API and LLM router functions while running on Modal with SQLite for application data and Modal's logging system for operational logs. This spec defines log structure, metrics, dashboards, and alert thresholds required for the MVP.

---

## Data Storage Architecture

**Application Data Storage:**
- **SQLite on Modal Volume**: User accounts, recipes, application state
- **Purpose**: Persistent application data that requires ACID transactions and structured queries

**Operational Data Storage:**
- **Modal Logging System**: Request logs, error logs, performance metrics, debug information
- **Purpose**: Operational observability, debugging, monitoring, alerting
- **Retention**: Managed automatically by Modal platform

**Separation Benefits:**
- Application performance not impacted by log volume
- Independent retention and access policies
- Modal handles log rotation, aggregation, and dashboard integration
- SQLite optimized purely for application data queries

## 1. Logging

### 1.1 Format

* **JSON per line** (NDJSON) to stdout. Modal collects and surfaces logs in dashboard; Loki integration can scrape.

* **Field schema**:

  | Field       | Type            | Example                                  | Notes                          |
  | ----------- | --------------- | ---------------------------------------- | ------------------------------ |
  | `ts`        | RFC 3339 string | `2025-06-23T19:02:11.123Z`               | UTC only                       |
  | `level`     | string          | `INFO`, `WARN`, `ERROR`                  |                                |
  | `service`   | string          | `api` \| `llm_router`                    |                                |
  | `req_id`    | UUID            | `70af…`                                  | Correlates logs across modules |
  | `user_id`   | UUID            | `18a0…`                                  | Optional (null for unauth)     |
  | `recipe_id` | UUID            | `f3db…`                                  | Optional                       |
  | `event`     | string          | `llm_call`, `db_query`, `auth_attempt`   |                                |
  | `msg`       | string          | Human message                            |                                |
  | `extra`     | object          | provider‑specific payload                | Free‑form JSON                 |

* **Library**: `structlog` configured with `structlog.processors.JSONRenderer()`.

### 1.2 Correlation IDs

* API entrypoint generates `req_id` (uuid4) per HTTP/WebSocket request and passes it via context var into LLM calls.
* All log entries for a single request share the same `req_id` for traceability.

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
| `websocket_connections_active`  | Gauge     | `recipe_id`                     | Active WebSocket connections |
| `auth_attempts_total`           | Counter   | `type`, `status`                | Authentication attempts    |
| `llm_call_tokens_total`         | Counter   | `provider`, `model_ref`, `role` | Prompt + completion tokens |
| `llm_call_latency_seconds`      | Histogram | `provider`, `model_ref`         | LLM response time          |
| `db_query_seconds`              | Histogram | `operation`                     | SQL latency                |

Buckets: `[0.1, 0.3, 1, 3, 10, 30, 60, 120]` seconds.

### 2.3 Error Budget & SLIs

| SLI                                       | Target             |
| ----------------------------------------- | ------------------ |
| API success rate (`2xx / total`)          | ≥ 99 % rolling 7 d |
| p95 API latency (`GET /v1/recipes/{id}`)  | < 200 ms           |
| p95 WebSocket message processing          | < 5 s              |
| Authentication success rate               | ≥ 95 % rolling 24h |

---

## 3. Alerting (Grafana Cloud)

| Alert                     | Condition                                                                | Severity | Action        |
| ------------------------- | ------------------------------------------------------------------------ | -------- | ------------- |
| **High API error rate**   | `5 min avg rate(http_request_total{status=~"5.."}) > 1/s`                | P1       | PagerDuty     |
| **Auth failures spike**   | `auth_attempts_total{status="failed"}` increase > 100 in 15 min          | P2       | Slack #alerts |
| **LLM latency**           | p95 `llm_call_latency_seconds` > 10 s for 5 min                          | P2       | Slack         |
| **DB slow queries**       | p95 `db_query_seconds{operation="INSERT recipes"} > 1 s` over 10 min     | P3       | Slack         |

---

## 4. Dashboards

* **API Overview** – Requests/s, latency percentiles, error codes.
* **Authentication** – Login attempts, success rates, password reset flows.
* **LLM Usage & Cost** – Token counters by provider/model, latency.
* **WebSocket Health** – Active connections, message rates, disconnection reasons.
* **DB Performance** – TPS, slowest queries, connections.

Dashboard JSON lives under `observability/grafana/` and is imported on Grafana startup.

---

## 5. Implementation Checklist

* [ ] Install `structlog`, `prometheus_client` in `requirements.txt`.
* [ ] Configure `structlog` JSON renderer in `app.__init__`.
* [ ] Middleware to generate `req_id` and push to context var.
* [ ] Decorator `@metric_timer` to wrap key functions (auth flows, LLM calls, WebSocket handlers).
* [ ] `observability/README.md` with Grafana import instructions.

---

*End of Logging & Monitoring Spec v0.1*