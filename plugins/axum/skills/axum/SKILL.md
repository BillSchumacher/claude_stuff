---
name: axum
description: "Applies when building or reviewing Axum web services. Covers extractors, error handling, tower middleware, shared state, and testing."
---

# Axum

## Routing and state

1. **`Router::nest` for prefixes, `Router::merge` for siblings.** Route definitions in separate modules.
2. **Shared state in `Arc`, passed via `Router::with_state`.** Extension is legacy; State is type-safe.
3. **Body-consuming extractors (Json, Multipart, Bytes) must be last** in handler signature.

## Error handling

4. **Custom error type with `IntoResponse`.** Centralized mapping, consistent JSON errors. Implement `From<sqlx::Error>` for `?`.
5. **`Result<T, AppError>` as return type for all handlers.**

## Middleware

6. **`middleware::from_fn` for simple, Tower Layer/Service for reusable.**
7. **`TraceLayer` from tower-http as outermost layer.** `tracing::instrument` for span-per-request.
8. **Apply CorsLayer explicitly — no CORS by default.** #1 reason browser clients fail.

## Production

9. **`with_graceful_shutdown(signal)` for clean shutdown.**
10. **`DefaultBodyLimit` or `RequestBodyLimitLayer`.** Default 2MB; unbounded = DoS.
11. **`.fallback(handler)` for proper 404 JSON.**
12. **`#[serde(deny_unknown_fields)]` on input types.** Rejects unexpected fields.

## Testing

13. **`tower::ServiceExt::oneshot` or axum-test crate.** No real TCP in unit tests.
