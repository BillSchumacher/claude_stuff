---
name: celery
description: "Celery best practices: task design, retry strategies, serialization, monitoring, rate limiting"
---

# Celery

## Task design

1. **Make every task idempotent.** Re-execution must produce same result. Use upserts; check state before mutating.
2. **Keep payloads small.** Pass IDs, not objects. JSON serialization only. Never pickle.
3. **Set both time limits.** `soft_time_limit` for cleanup, `time_limit` kills process. time_limit > soft_time_limit.

## Retry and reliability

4. **Exponential backoff retries.** `autoretry_for`, `retry_backoff=True`, `retry_jitter=True`, `max_retries`.
5. **`acks_late=True` + `task_reject_on_worker_lost=True` for critical tasks.** Re-queues on worker death. Only with idempotent tasks.
6. **Choose broker deliberately.** RabbitMQ for reliability/routing. Redis for simplicity. Redis loses tasks on crash without persistence.

## Configuration

7. **Disable result backend if unused.** Saves overhead. If needed, set `result_expires`.
8. **Route tasks to dedicated queues.** Separate CPU, I/O, and quick tasks.
9. **`worker_prefetch_multiplier=1` for long tasks.** Default 4 grabs tasks workers can't process promptly.
10. **Rate-limit external API calls.** `rate_limit="10/m"` per worker.

## Patterns

11. **`chain` for sequential, `group` for parallel, `chord` for fan-out-aggregate.** Never nest chords with Redis.
12. **Monitor with Flower.** Alert on failures and queue depth.
13. **Never long DB transactions inside tasks.** Commit early.
14. **`task_always_eager=True` only in tests.**
