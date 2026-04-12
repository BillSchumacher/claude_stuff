---
name: fastapi
description: "Applies when building or reviewing FastAPI applications. Covers dependency injection, Pydantic v2, async endpoints, security, and testing."
---

# FastAPI

## Dependency injection

1. **Use `Depends()` for all shared logic: DB sessions, auth, pagination.** Cached per-request by default.
2. **Manage DB sessions with yield dependency.** Commit/rollback per-request, close in finally.
3. **Use `Annotated` types (3.9+):** `DB = Annotated[AsyncSession, Depends(get_db)]`.

## Async and Pydantic

4. **`async def` only for async I/O.** Plain `def` auto-runs in threadpool. `async def` with sync blocking code blocks the event loop.
5. **Pydantic v2 BaseModel for all schemas.** `ConfigDict(from_attributes=True)` for ORM. `Field()` for validation.
6. **Set `response_model` for response filtering.** Return type alone generates docs but doesn't filter fields.

## Architecture

7. **Lifespan context manager, not `@app.on_event`.**
8. **Prefer dependencies over middleware** for request-scoped logic. Middleware runs on every request including docs/static.
9. **APIRouter for modular organization.** Feature modules with prefix and tags.
10. **HTTPException for errors.** Custom exception handlers for domain errors.

## Security and testing

11. **OAuth2PasswordBearer or APIKeyHeader as dependencies.** Integrates with OpenAPI spec.
12. **TestClient for sync, httpx.AsyncClient for async.** Override deps with `app.dependency_overrides`.
13. **Set `status_code` on decorators** for correct codes and OpenAPI spec.
14. **UploadFile for files, not raw bytes.** Spills to disk, prevents OOM.
15. **Disable docs in production:** `FastAPI(docs_url=None, redoc_url=None)`.
