---
name: asp-net
description: "ASP.NET Core best practices: DI lifecycle, middleware pipeline, configuration, EF Core, health checks"
---

# ASP.NET Core

## Dependency injection

1. **Choose lifetimes correctly.** Singleton: stateless. Scoped: per-request (DbContext). Transient: lightweight disposables. Never inject scoped into singleton (captive dependency).
2. **Options pattern for configuration.** Bind sections to typed classes. IOptionsSnapshot for reloadable, IOptionsMonitor for singletons.

## Middleware

3. **Order matters.** ExceptionHandler, HSTS, HTTPS redirect, StaticFiles, Routing, CORS, Authentication, Authorization, MapControllers.
4. **ProblemDetails (RFC 9457) for error responses.**
5. **CORS: never AllowAnyOrigin with AllowCredentials.**

## Logging and EF Core

6. **Structured logging with `ILogger<T>`.** Never string interpolation in log calls.
7. **DbContext as scoped with pooling.** AddDbContextPool reuses instances.

## API patterns

8. **Minimal APIs for simple endpoints, controllers for complex.**
9. **Return Results with proper status codes.** Never exceptions for control flow.
10. **Cancellation tokens throughout.** Stop wasted work on client disconnect.

## Background and health

11. **BackgroundService for background work.** Create scope inside for scoped dependencies. Never Task.Run in handlers.
12. **Health checks for all dependencies.** Map to /health.

## Security

13. **Secrets in User Secrets (dev) or env/vault (prod).** Never appsettings.json.
14. **Explicit `[FromBody]`, `[FromQuery]`.** Prevent over-posting.
15. **Output caching for read-heavy endpoints.**
