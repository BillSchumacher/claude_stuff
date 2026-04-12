---
name: django
description: "Applies when building or reviewing Django applications. Covers ORM optimization, middleware, security, caching, migrations, and async views."
---

# Django

## ORM performance

1. **Use `select_related()` for ForeignKey/OneToOne, `prefetch_related()` for ManyToMany/reverse FK.** Every template or serializer touching a related object without these creates N+1 queries.
2. **QuerySets are lazy.** `.count()`, `.exists()`, `len()`, `list()`, `bool()`, and iteration trigger evaluation. Chain filters freely.
3. **Use `.only()` and `.defer()` to limit columns.** Accessing a deferred field triggers a per-instance query. Prefer `.values()` when you don't need instances.
4. **Use `bulk_create()` and `bulk_update()` for batch operations.** `bulk_create(objs, batch_size=1000)` is one query, not 1,000.
5. **Use `F()` expressions for atomic updates.** `Model.objects.filter(pk=pk).update(counter=F('counter') + 1)` avoids race conditions.
6. **Index columns in `filter()`, `order_by()`, `exclude()`.** Use `db_index=True` or `Meta.indexes` for composites.

## Security and configuration

7. **Never put SECRET_KEY or credentials in settings.py.** Read from env vars with crash on missing in production.
8. **Split settings: base.py, dev.py, prod.py.** prod.py: `DEBUG=False`, `ALLOWED_HOSTS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`.
9. **Middleware ordering matters.** SecurityMiddleware, SessionMiddleware, CommonMiddleware, CsrfViewMiddleware, AuthenticationMiddleware, MessageMiddleware.
10. **Never disable CSRF unless building a pure token-auth API.** For AJAX, pass token via X-CSRFToken header.
11. **Set ALLOWED_HOSTS explicitly.** Empty list + DEBUG=False rejects all. Wildcard enables host-header injection.

## Caching and static files

12. **Cache in layers:** per-view (`@cache_page`), template fragment (`{% cache %}`), low-level (`cache.get/set`). Set KEY_PREFIX.
13. **Serve static with WhiteNoise or CDN.** Run `collectstatic` in build. Serve media from object storage.

## Migrations and signals

14. **Squash migrations periodically.** Never edit applied migrations. Use RunPython with reverse_code.
15. **Avoid signals for business logic.** Invisible coupling. Prefer explicit service functions.

## Async and connections

16. **Async views (4.1+): wrap ORM in `sync_to_async()` or use async ORM methods** (`aget()`, `async for`). Sync ORM in async view raises SynchronousOnlyOperation.
17. **Set CONN_MAX_AGE nonzero (e.g., 600) in production.** Default 0 opens/closes per request.
18. **Use `get_object_or_404()` in views.** Uncaught DoesNotExist leaks 500 errors.
