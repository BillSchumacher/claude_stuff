---
name: observability
description: Applies when implementing any service, handler, background worker, or I/O boundary that will run in production. Enforces OpenTelemetry instrumentation (spans, attributes, exception recording), structured stdout logging with trace correlation, and SLI/SLO discipline from OpenTelemetry semantic conventions, Google SRE Workbook, and 12-Factor App.
---

# Observability & Instrumentation

Apply these rules to every service, handler, worker, or I/O boundary you write. Code without observability is unoperable in production.

## Trace every I/O boundary

- **Wrap each I/O boundary in an OpenTelemetry span.** This includes HTTP handlers, database queries, outbound HTTP calls, queue producers/consumers, and external service calls.
- **Set `SpanKind` correctly:**
  - `SERVER` — incoming HTTP/RPC handlers
  - `CLIENT` — outbound HTTP/RPC calls, DB queries
  - `PRODUCER` — publishing to a queue
  - `CONSUMER` — receiving from a queue
- **Use semantic attribute names** from OpenTelemetry semantic conventions:
  - HTTP spans: `http.request.method`, `http.response.status_code`, `url.path`, `server.address`
  - DB spans: `db.system`, `db.operation`, `db.namespace` (database name), `db.statement` only if not sensitive
  - Messaging: `messaging.system`, `messaging.destination.name`, `messaging.operation`

## Record exceptions, set span status

- **In every `except` block that handles a non-trivial error:**
  - `span.record_exception(exc)`
  - `span.set_status(Status(StatusCode.ERROR, str(exc)))`
- Do not swallow exceptions silently. If you re-raise, the parent span will see the error too.

## Structured logging to stdout

- **Logs are structured JSON written to stdout.** Never write logs to files, never use `RotatingFileHandler` or `TimedRotatingFileHandler` from inside the app — that's the runtime's job (12-Factor XI: logs are event streams).
- **Use a structured logger** (`structlog`, `python-json-logger`, or a `logging.Formatter` that emits JSON), not `print()`.
- **Every log line at WARN or above must include `trace_id` and `span_id`** so the log correlates to the trace it belongs to. Most OTel logging integrations do this automatically.
- **Never log secrets, tokens, passwords, full PII, or full request/response bodies.** Redact at the logging boundary.

## SLI/SLO discipline (for services that face users or other services)

- **Define at least one Service Level Indicator** as `good_events / total_events`. Examples:
  - HTTP service: `(non-5xx requests) / (total requests)`
  - Worker: `(messages processed without retry) / (total messages)`
  - Pipeline: `(records written) / (records read)`
- **Set an explicit Service Level Objective** below 100% (e.g., 99.5%). Document the time window (e.g., 28-day rolling).
- **Alert on SLO burn rate**, not on raw CPU/memory thresholds. Burn rate alerts surface real user impact.

## Health checks vs metrics

- **Liveness check** (`/healthz` or equivalent): is the process running? Returns 200 if the process is up. Cheap, no dependencies.
- **Readiness check** (`/readyz`): is the process ready to serve traffic? Verifies dependencies (DB, downstream services) are reachable.
- **Metrics endpoint** (`/metrics`): exposes Prometheus-format counters/gauges/histograms (or OTLP push to a collector). Don't conflate it with health checks.

## When this skill conflicts with the request

If the request says "just print() it for now", "skip the spans", or "log to a file", explain the impact (logs that don't ship to the aggregator, traces with no correlation, etc.) and offer the proper instrumentation. Do not silently comply.

## Sources

- OpenTelemetry Semantic Conventions — https://opentelemetry.io/docs/specs/semconv/
- Google SRE Workbook (Implementing SLOs) — https://sre.google/workbook/implementing-slos/
- Google SRE Workbook (Alerting on SLOs) — https://sre.google/workbook/alerting-on-slos/
- 12-Factor App — Logs — https://12factor.net/logs
