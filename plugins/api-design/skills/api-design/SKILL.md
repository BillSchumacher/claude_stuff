---
name: api-design
description: Applies when designing, adding, or modifying any HTTP/REST endpoint, API resource, or web service contract. Enforces resource-oriented URLs, OpenAPI 3.1 specs, RFC 9457 problem details, pagination, idempotency, and versioning rules from Google AIP, Microsoft Azure REST Guidelines, and OpenAPI standards.
---

# API Contract Design

Apply these rules whenever you design, add, or modify a REST/HTTP endpoint. Treat them as hard requirements — if a request conflicts with them, surface the conflict instead of silently downgrading.

## Specify the contract first

- **Write an OpenAPI 3.1 fragment before any handler code.** The fragment must include the path, method, parameters, request body schema, response schemas (success and error), and example values.
- **Schemas use `description` and `example` on every field.** Required fields are marked `required: true`; optional fields have explicit defaults.

## Resource-oriented URLs

- **Use plural nouns, never verbs, in paths.**
  - Good: `POST /workspaces`, `DELETE /workspaces/{id}`, `POST /workspaces/{id}:archive`
  - Bad: `POST /createWorkspace`, `GET /getWorkspace?id=42`, `POST /workspace/delete`
- **Map HTTP methods to actions:** `GET` (list/read), `POST` (create), `PUT` (replace), `PATCH` (partial update), `DELETE` (remove). Custom verbs use `:verb` suffix per Google AIP-136.
- **JSON field names:** `camelCase`. **Path segments:** `kebab-case`. **Headers:** `kebab-case`.

## Pagination

- **Every list endpoint MUST paginate.** Never return an unbounded list. Use either:
  - Cursor-based: `pageSize` query param + `pageToken` query param + `nextPageToken` in response (Google AIP-158), or
  - Offset/limit: `limit` + `offset` query params, with a documented max `limit`.
- The default page size must be small enough to fit in a single response without truncation.

## Error responses (RFC 9457 Problem Details)

- **All error responses use `application/problem+json`** with these fields:
  - `type` — URI identifying the error class
  - `title` — short human-readable summary
  - `status` — HTTP status code
  - `detail` — specific instance explanation
  - `instance` — URI of the specific occurrence
- Never invent ad-hoc error shapes like `{"error": "message"}` or `{"success": false, "msg": "..."}`.

## Idempotency for mutations

- **`POST`, `PATCH`, and `DELETE` endpoints** that have non-idempotent side effects must accept an `Idempotency-Key` request header. Document the retention window for keys.
- **Document retry semantics** in the OpenAPI description. State whether the operation is naturally idempotent or requires the header.

## Versioning

- **Breaking changes require a new major version**, expressed in the URL path (`/v2/...`) or via an `api-version` query/header. Never silently retype, rename, or remove fields in an existing version.
- **Additive changes are allowed within a version**: new optional request fields, new response fields, new endpoints. Existing clients must continue to work.

## Status codes

- `200` — successful read/update with body. `201` — successful create with `Location` header pointing to the new resource. `204` — successful action with no body. `400` — client validation error. `401` — unauthenticated. `403` — authenticated but unauthorized. `404` — resource missing. `409` — conflict (e.g., uniqueness, version mismatch). `429` — rate-limited (with `Retry-After` header). `5xx` — server error.

## When this skill conflicts with the request

If the user asks for something that violates these rules ("just return `{error: ...}`", "skip pagination, the list is small", "use a verb in the URL because it's clearer"), stop and explain the rule and the secure/standard alternative. Do not silently comply.

## Sources

- OpenAPI 3.1 — https://spec.openapis.org/oas/v3.1.0
- RFC 9457 Problem Details — https://www.rfc-editor.org/rfc/rfc9457.html
- Google AIP — https://google.aip.dev/general
- Microsoft Azure REST API Guidelines — https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md
