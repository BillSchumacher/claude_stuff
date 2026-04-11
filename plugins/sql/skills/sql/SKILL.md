---
name: sql
description: Dialect-neutral SQL best practices: query performance, schema design, naming conventions, transactions, migrations, anti-patterns
---

# SQL Best Practices

When generating SQL queries, schemas, or migrations, apply every applicable rule below. These are dialect-neutral; load a `sql-{dialect}` skill alongside this one for dialect-specific patterns.

## Query performance

1. **Never use `SELECT *` in production code.** List only the columns needed. `SELECT *` breaks covering indexes and causes silent breakage when schema changes.
2. **Create indexes for every `WHERE`, `JOIN`, and `ORDER BY` column in frequent queries.** Composite indexes: equality filters first, then range filters, then sort columns (leftmost-prefix rule).
3. **Use `EXPLAIN` (or `EXPLAIN ANALYZE`) before deploying any query on non-trivial tables.** Watch for sequential scans, nested loops on unindexed columns, sort spills.
4. **Never wrap indexed columns in functions.** `WHERE YEAR(created_at) = 2025` kills the index. Rewrite as `WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01'`.
5. **Use `EXISTS` instead of `IN` for correlated existence checks** on large result sets. `EXISTS` short-circuits on first match.
6. **Never use `OFFSET` for deep pagination.** Use keyset pagination: `WHERE id > :last_seen ORDER BY id LIMIT :n`.
7. **Batch bulk inserts.** Multi-row `INSERT ... VALUES (...),(...),...` or `COPY`/bulk-load. Never one row per round-trip.
8. **Avoid `OR` across different columns** — it prevents index usage. Rewrite as `UNION ALL` of indexed queries.

## Schema design

9. **Start at 3NF.** Denormalize only after measuring, and document the reason.
10. **Use the narrowest data type.** `SMALLINT` over `INT` when it fits, `DATE` not `TIMESTAMP` for calendar dates, `NUMERIC(p,s)` not `FLOAT` for money.
11. **Every table must have a primary key.** Prefer surrogate BIGINT PKs. For UUIDs, use UUIDv7 (ordered) to reduce index fragmentation.
12. **Declare `NOT NULL` on every column** unless NULL has defined semantics.
13. **Add `CHECK` constraints** for domain validation (`CHECK (price >= 0)`, `CHECK (status IN ('active','inactive'))`).
14. **Declare foreign keys.** Even without enforcement, they document relationships and help query planners.
15. **Add `UNIQUE` constraints** on natural-key columns (email, username) even with surrogate PKs.
16. **Use `TIMESTAMP WITH TIME ZONE`** for point-in-time values. Store UTC, convert in the presentation layer.
17. **Add `created_at` and `updated_at`** to every mutable table with defaults and auto-update triggers.

## Naming conventions

18. **`snake_case` for all identifiers.** Never camelCase or PascalCase in SQL.
19. **Singular table names** (`user`, `order`, `product`).
20. **Boolean columns: `is_*` or `has_*`** (`is_active`, `has_verified_email`).
21. **Foreign key columns: `<table>_id`** (`user_id`, `order_id`).
22. **Index names: `ix_<table>_<cols>`**, unique: `ux_<table>_<col>`, foreign keys: `fk_<table>_<ref>`.
23. **Avoid reserved words** (`user`, `order`, `group`). Rename to `app_user`, `customer_order`, etc.

## Transactions

24. **Keep transactions short.** Never hold a transaction open during HTTP calls, file I/O, or user input.
25. **Use `READ COMMITTED` as the default isolation.** Document explicitly when using higher levels.
26. **Access tables in consistent order** across transactions to prevent deadlocks.
27. **Use optimistic concurrency** (version columns) for long-running operations instead of long-held locks.
28. **Retry on deadlock/serialization errors** (SQLSTATE 40001, 40P01) with exponential backoff.

## Migrations

29. **Make every migration idempotent.** `IF NOT EXISTS`, `IF EXISTS` guards on all DDL.
30. **Never drop or rename a column in one deployment.** Expand-contract: add new → backfill → migrate readers → drop old.
31. **Add indexes concurrently** when supported (`CONCURRENTLY` in PG, `ALGORITHM=INPLACE` in MySQL).
32. **Separate schema migrations from data migrations.** Schema changes should be instant; data backfills are separate batch jobs.
33. **Every migration must have a rollback path.**

## Anti-patterns

34. **N+1 queries:** fetch list then query per item. Use `JOIN` or `IN (...)`.
35. **Implicit type coercion:** `WHERE varchar_col = 12345` casts every row, kills indexes.
36. **`SELECT DISTINCT` to hide bad joins.** Fix the join conditions.
37. **Correlated subqueries when `JOIN` or window functions suffice.**
38. **`HAVING` for conditions that belong in `WHERE`.** `WHERE` filters before aggregation.
39. **Comma-separated values in a column.** Use a junction table.
40. **Soft-delete `is_deleted` without a partial index.** Add a partial index on active rows.
41. **`FLOAT`/`DOUBLE` for money.** Use `NUMERIC`/`DECIMAL`.

## NULL handling

42. **`IS NULL` / `IS NOT NULL`, never `= NULL`.** `= NULL` evaluates to UNKNOWN.
43. **`COALESCE(expr, default)`** for fallback values.
44. **`NOT IN` with NULLs returns no rows.** Use `NOT EXISTS` instead.
45. **`COUNT(*)` counts rows; `COUNT(col)` skips NULLs.** Choose deliberately.

## Window functions vs GROUP BY

46. **`GROUP BY`** when you need one row per group (aggregation that reduces rows).
47. **Window functions** when you need aggregation alongside original rows (running totals, rankings, lag/lead).
48. **`ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)`** for top-N-per-group. Never use correlated subqueries for this.
49. **Name window definitions: `OVER w ... WINDOW w AS (...)`** for reuse.

## CTEs vs subqueries

50. **CTEs for readability** when referenced multiple times or for distinct logical steps.
51. **Be aware CTEs may be optimization fences** in some databases. Test if inline subqueries are faster for single-use derived tables.
52. **Recursive CTEs** for hierarchies. Always include termination (depth counter or `CYCLE` clause).
