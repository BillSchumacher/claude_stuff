---
name: redis
description: "Applies when integrating or reviewing Redis usage. Covers connection pooling, pipelining, data structures, TTL, memory management, and pub/sub."
---

# Redis

## Connections and performance

1. **Always connection pool.** One pool per process. Per-command connections are catastrophically slow.
2. **Pipeline batch operations.** Groups commands into one round-trip.
3. **TTL on every key.** No TTL = unbounded growth until OOM. maxmemory-policy as backstop.
4. **Never KEYS in production.** Blocks single-threaded server. Use SCAN with cursor.
5. **No large blobs (>100KB).** Large GETs block all clients. Store references instead.

## Data structures

6. **Right structure for the job.** Strings: cache. Hashes: objects. Sorted sets: leaderboards. Sets: membership. Streams: events. Lists: FIFO queues.
7. **Colon-separated key namespaces.** `app:users:42:profile`.

## Atomicity and persistence

8. **Lua scripts for atomic multi-step operations.**
9. **RDB for snapshots, AOF for durability.** Both in production.
10. **UNLINK over DEL for large keys.** DEL blocks; UNLINK is async.

## HA and config

11. **Sentinel for HA, Cluster for scaling.** Don't Cluster if data fits one node.
12. **Set maxmemory and maxmemory-policy.** allkeys-lru for caches, noeviction for primary data.
13. **Retry on connection errors.** retry_on_timeout, socket timeouts, health_check_interval.
14. **MULTI/EXEC sparingly.** No rollback. Lua usually better.
