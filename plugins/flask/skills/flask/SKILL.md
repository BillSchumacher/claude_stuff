---
name: flask
description: "Applies when building or reviewing Flask applications. Covers application factory, blueprints, context management, extensions, and production deployment."
---

# Flask

## Application structure

1. **Always use the application factory pattern.** `create_app()` returns a configured Flask instance. Enables testing, avoids circular imports.
2. **Use Blueprints for modularity.** Each feature area gets its own Blueprint with routes, models, templates. Register with URL prefixes.
3. **Avoid circular imports by deferring extension init.** `db = SQLAlchemy()` at module level, `db.init_app(app)` inside factory.

## Configuration and security

4. **Never `app.run()` in production.** Deploy with gunicorn/waitress. Set `debug=False` explicitly.
5. **Load config from env vars.** `app.config.from_prefixed_env()` (2.2+) or `os.environ`. Never commit SECRET_KEY.
6. **Set SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=True (prod), SESSION_COOKIE_SAMESITE='Lax'.** Not defaults.

## Error handling and context

7. **Register error handlers for common HTTP errors** and unhandled exceptions. Log exceptions server-side.
8. **Understand app context vs request context.** `current_app`/`g` need app context. `request`/`session` need request context. Use `with app.app_context():` in CLI/background tasks.

## Database and testing

9. **Use Flask-Migrate (Alembic), not `db.create_all()`.** create_all can't alter existing tables.
10. **Wrap commits in try/except with rollback on failure.**
11. **Use `test_client()` from factory.** Fixture builds app with test config, yields client.

## Production

12. **Return dicts or `jsonify()` for JSON APIs.** Never manual `json.dumps()`.
13. **Rate-limit with flask-limiter.** Auth and API endpoints.
14. **Validate uploads:** allowlist extensions, `MAX_CONTENT_LENGTH`, `secure_filename()`. Store to object storage.
