---
name: htmx
description: "htmx best practices: HTML fragments, hx-target/swap, CSRF headers, HX-Trigger events, progressive enhancement"
---

# htmx

## Architecture

1. **Return HTML fragments, never full pages.** Every htmx endpoint returns only the markup for the swap target. No `<html>`, `<head>`, or `<body>`.
2. **Follow HATEOAS — server drives available actions.** Include next-possible actions as htmx-annotated links/buttons in every response fragment. The client never constructs URLs.
3. **Keep state in the DOM, not JavaScript.** Use `id` attributes as source of truth. Avoid shadow state in JS objects.
4. **Use `hx-boost="true"` on `<body>` or nav containers** for progressive enhancement. Upgrades `<a>` and `<form>` to AJAX automatically with graceful degradation.

## Core patterns

5. **Always set an explicit `hx-target`.** Default is the triggering element's innerHTML — almost never what you want. Forgetting `hx-target` is the #1 htmx bug.
6. **Choose `hx-swap` deliberately.** `innerHTML` for filling containers. `outerHTML` for replacing the element itself (response must include the wrapper). `beforeend` for appending to lists. `delete` for removals. `none` for fire-and-forget.
7. **Use `hx-select` only when you can't control the server response.** Prefer dedicated partial endpoints.

## Security

8. **Include CSRF tokens via `hx-headers` on `<body>` for all state-changing requests.** Refresh on `htmx:configRequest` for long-lived pages.
9. **Validate and sanitize everything server-side.** htmx fragments are HTML injection surfaces. Use template auto-escaping (Jinja2, Razor). Treat htmx endpoints with the same rigor as full-page endpoints.
10. **Use correct HTTP verbs.** `hx-get` for reads, `hx-post` for creates, `hx-put`/`hx-patch` for updates, `hx-delete` for deletes. GET typically bypasses CSRF.

## Performance

11. **Show loading states with `hx-indicator`.** Point to a spinner element. htmx adds/removes `htmx-request` class automatically.
12. **`hx-push-url="true"` on navigation requests** for browser history and shareable URLs. Server detects `HX-Request` header: return fragment for htmx, full page for direct navigation.
13. **Lazy-load with `hx-trigger="revealed"`.** Combine with skeleton placeholders for perceived performance.

## Forms

14. **Put `hx-post` on the `<form>`, not the submit button.** Button-level `hx-post` sends only the button, not form data.
15. **`hx-trigger` modifiers for debounce/throttle.** `delay:300ms` for search-as-you-type, `throttle:` for scroll, `changed` to fire only on value change, `from:` for listening on other elements.
16. **`hx-confirm` on destructive actions.** Browser-native confirmation dialog.

## Server integration

17. **HTTP status codes as control flow.** `200` = normal swap. `204` = do nothing (not empty 200, which clears the target). `286` = stop polling.
18. **`HX-Trigger` response headers for cross-component updates.** Fire client-side events that other elements listen for with `hx-trigger="eventName from:body"`. Primary mechanism for loose coupling.
19. **`hx-swap-oob="true"` for multi-region updates.** Append elements with matching IDs after the primary fragment. Prefer `HX-Trigger` for loose coupling; use OOB sparingly.
20. **`HX-Redirect` / `HX-Refresh` headers for full-page navigation** after login, logout, or context changes. Don't return a fragment when the whole page context changed.

## Gotchas

21. **Nested `hx-boost` inherits.** Set `hx-boost="false"` on file downloads and external links.
22. **Stale CSRF tokens on cached pages.** Use `htmx:configRequest` to read fresh token from cookie/meta.
23. **Empty 200 clears the target.** Use `204` to leave DOM untouched.
24. **Polling without stop condition.** Always handle `286` or use `hx-trigger="every 2s [condition]"`.
25. **Missing `id` on OOB targets.** `hx-swap-oob` silently fails if IDs don't match.
