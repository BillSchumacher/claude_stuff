---
name: rabbitmq
description: "Applies when building or reviewing RabbitMQ messaging systems. Covers exchanges, durable queues, acknowledgments, dead letters, and publisher confirms."
---

# RabbitMQ

## Durability

1. **Durable queues + persistent messages (delivery_mode=2).** Without both, lost on restart.
2. **Manual acknowledgments.** Auto-ack loses messages on crash. Ack after processing; reject requeue=False to dead-letter.
3. **prefetch_count for concurrency.** 1 for slow tasks, 10-50 for fast.

## Routing

4. **Right exchange type.** Direct: exact key. Topic: patterns (order.*). Fanout: broadcast. Headers: rare.
5. **Dead letter exchanges for failures.** Don't silently drop or infinitely requeue.
6. **Message TTL and queue length limits.** x-overflow=reject-publish for backpressure.

## Reliability

7. **Publisher confirms.** Without them, broker may silently drop under memory pressure.
8. **Quorum queues for HA.** Classic mirrored deprecated in 3.13+. Quorum uses Raft.

## Connections

9. **One connection per app (TCP). Multiple channels (lightweight).** Never share channels across threads.
10. **Separate connections for pub and consume.** Blocked pub can starve consumer heartbeat.
11. **Heartbeats + reconnection logic.**
12. **x-single-active-consumer for ordered processing.**
13. **Monitor queue depth, consumers, rates.** Alert on growth or zero consumers.
