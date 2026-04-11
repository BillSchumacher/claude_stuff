---
name: sqlalchemy
description: "SQLAlchemy best practices: session lifecycle, eager loading, connection pooling, 2.0 style, Alembic"
---

# SQLAlchemy

## 2.0 style

1. **Use 2.0-style queries.** `select()`, `Session.execute()`, `Session.scalars()`. Legacy Query is deprecated.
2. **`Mapped[]` type annotations** with `mapped_column()`.
3. **`relationship` with `back_populates`, not `backref`.** Explicit, type-checkable.

## Session lifecycle

4. **One session per request, closed at end.** Middleware or dependency. Never share across threads.
5. **`expire_on_commit=False`** when reading after commit. Default expires attributes, causing extra SELECTs.
6. **Never commit inside a loop.** Batch changes, commit once.

## Eager loading

7. **Prevent N+1 with explicit eager loading.** Default lazy fires a query per relationship access.
8. **`joinedload`** few parents/few children. **`selectinload`** many parents. **`subqueryload`** complex filters.
9. **No lazy loading in async.** Triggers implicit I/O, fails with MissingGreenlet.

## Pooling and async

10. **Configure pooling:** `pool_size`, `max_overflow`, `pool_pre_ping=True`, `pool_recycle=1800`.
11. **Async engine for async frameworks.** `create_async_engine("postgresql+asyncpg://...")`.

## Bulk and migrations

12. **Bulk operations for batches.** `session.execute(insert(User), [{...}])` not looped `session.add()`.
13. **`server_default` for DB-level defaults**, not `default` (Python-side, skipped in bulk).
14. **Alembic for all schema changes.** Never `metadata.create_all()` in production.
