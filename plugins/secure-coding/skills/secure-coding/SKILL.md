---
name: secure-coding
description: Use when designing or implementing any feature, fix, or refactor that touches user input, authentication, authorization, secrets, cryptography, file/network I/O, deserialization, dependencies, error handling, or logging. Enforces actionable rules from OWASP Top 10:2025, ASVS 5.0, OWASP Proactive Controls 2024, NIST SSDF (SP 800-218 / 800-218A), and NIST CSF 2.0.
---

# Secure Coding

Apply these rules to every design and implementation. They are derived from the current versions of OWASP Top 10:2025, OWASP ASVS 5.0, OWASP Proactive Controls 2024, NIST SSDF SP 800-218 / 800-218A, and NIST Cybersecurity Framework 2.0.

Treat each rule as a hard constraint, not a suggestion. If a rule conflicts with a request, surface the conflict — do not silently downgrade.

## Input handling

- **Validate every input at the trust boundary** using an allowlist (type, length, range, format). Treat HTTP, files, env vars, IPC, sockets, queue messages, and deserialized payloads as hostile until validated. *(OWASP Top 10 A05, ASVS V1, Proactive C3)*
- **Use parameterized queries / prepared statements** for SQL, NoSQL, LDAP, OS commands, and ORM raw queries. **Never** concatenate or f-string user input into a query. *(Top 10 A05, ASVS V1.2/V5, Proactive C3, SSDF PW.5)*
- **Context-aware output encoding** for HTML, HTML attributes, JS, CSS, and URL contexts. Prefer framework auto-escaping. Never disable it (`dangerouslySetInnerHTML`, `\|safe`, `v-html`, `Markup(...)`). *(Top 10 A03, Proactive C3)*
- **Safe deserialization only.** Do not use Python `pickle`, Java `ObjectInputStream`, PHP `unserialize`, or YAML `load()` on untrusted data. Prefer JSON with schema validation. *(Top 10 A08)*
- **Safe file operations.** Canonicalize paths, reject `..` traversal, constrain to an allowlisted base directory, validate MIME by content (not extension), store uploads outside the web root. *(Top 10 A01)*
- **Prevent SSRF.** Allowlist outbound hosts; block link-local and metadata IPs (`169.254.169.254`, RFC1918, `127.0.0.0/8`, `::1`); disable cross-host redirects on HTTP clients. *(Proactive C10)*
- **Disable XML external entities** in every XML parser used (`defusedxml` in Python, `XMLConstants.FEATURE_SECURE_PROCESSING` in Java). *(Top 10 A05)*

## Authentication & authorization

- **Enforce authorization on every request, server-side, deny-by-default.** Check it on the object, not just the route. Reject sequential/guessable IDs that enable IDOR. No client-side-only checks. *(Top 10 A01, Proactive C1, ASVS V4, SP 800-53 AC-3, AC-6)*
- **Apply least privilege everywhere** — DB grants, IAM roles, container capabilities, file permissions. Read-only filesystems where possible. *(SP 800-53 AC-6, CSF 2.0 PR.AA, Proactive C1)*
- **Use standards-based authentication** (OIDC, OAuth 2.1, WebAuthn). Never invent custom auth. Rate-limit and lock out on failed attempts. Rotate session IDs on login. *(Top 10 A07, Proactive C7, ASVS V2/V3, SP 800-63B)*
- **Cookies for sessions must be `HttpOnly`, `Secure`, `SameSite=Lax` or stricter.** *(Top 10 A07)*
- **CSRF protection** on every state-changing request: SameSite cookies plus anti-CSRF tokens or double-submit pattern. *(OWASP Cheat Sheet: CSRF Prevention)*

## Cryptography & secrets

- **Never hardcode secrets, API keys, tokens, passwords, or private keys** in source, config, tests, fixtures, or comments — not even as placeholders. Load from env vars, secret managers (Vault, AWS/GCP/Azure secret services), or platform keystores. Add patterns to `.gitignore` and pre-commit secret scanners. *(Top 10 A02/A04, ASVS V6, SSDF PS.1)*
- **Use vetted cryptographic libraries; never roll your own crypto.**
  - Symmetric: AES-GCM or ChaCha20-Poly1305.
  - Password hashing: Argon2id (preferred), scrypt, or bcrypt with appropriate cost.
  - General hashing: SHA-256 or stronger.
  - **Forbidden:** MD5, SHA-1, DES, 3DES, ECB mode, static IVs, static salts, custom KDFs.
  - *(Top 10 A02, Proactive C2, ASVS V6)*
- **Generate randomness with cryptographically secure RNGs** for tokens, IDs, keys, nonces, and salts: Python `secrets`, Node `crypto.randomBytes`, Java `SecureRandom`, Go `crypto/rand`. **Never** `Math.random`, `rand()`, `random.random()`, `time(NULL)`. *(Proactive C2)*
- **TLS 1.2+ (prefer 1.3)** for all network traffic. Verify certificates. Set HSTS on web responses. Never `verify=False`, `TrustAllCerts`, `InsecureSkipVerify`, or plaintext HTTP for auth or sensitive data. *(Top 10 A02)*

## Dependencies & supply chain

- **Pin and lockfile all dependencies.** Use language-native lockfiles (`Pipfile.lock`, `package-lock.json`, `go.sum`, `Cargo.lock`). *(Top 10 A03/A08, SSDF PW.4)*
- **Scan dependencies in CI** (Dependabot, Snyk, OSV-Scanner, `pip-audit`, `npm audit`). Treat critical/high CVEs as build failures. *(SSDF PS.3, CSF 2.0 ID.SC)*
- **Generate and publish SBOMs** (CycloneDX or SPDX). *(EO 14028, SSDF PS.3)*
- **Verify package authenticity** — checksums, signatures, and known-good registries. Be paranoid about typosquatted package names; double-check spelling against the official registry before adding a new dependency. *(SSDF PS.2)*
- **Pin GitHub Actions to commit SHAs**, not tags. Use signed commits and protected branches. *(SSDF PS.2/PS.3)*
- **Remove unused dependencies.** Each one is attack surface.

## Configuration & defaults

- **Secure-by-default configuration** in every environment:
  - Disable debug, verbose error pages, and stack traces in non-dev environments.
  - Disable directory listing.
  - Set security headers: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer-when-downgrade`, `Strict-Transport-Security`.
  - Change or remove default credentials and accounts.
  - *(Top 10 A02/A05, Proactive C5, SSDF PW.9)*
- **Threat-model before implementing security-sensitive features**: auth, payments, file upload, IPC, deserialization, crypto, multi-tenant data access. *(Top 10 A04 Insecure Design, Proactive C4, SSDF PW.1)*

## Error handling & logging

- **Handle errors and exceptions explicitly.** Fail closed, not open. **Never `except: pass`** or swallow exceptions silently. Never return raw stack traces, SQL errors, or internal paths to the user. *(Top 10 A10, OWASP Cheat Sheet: Error Handling)*
- **Log security-relevant events** with timestamps, user ID, source IP, and outcome: authentication success/failure, authorization denials, input validation failures, admin actions, password/key changes. *(Top 10 A09, Proactive C9, CSF 2.0 DE.CM, SP 800-53 AU family)*
- **Never log secrets, tokens, passwords, full PAN/PII, session IDs, JWTs, or full request bodies.** Redact before logging. *(Top 10 A09)*

## Testing security

- **Write security tests.** Unit tests for authorization boundaries; fuzz tests for parsers and deserializers; SAST and DAST in CI. *(SSDF PW.7/PW.8, Proactive C4)*
- **Add a regression test for every security fix.** *(SSDF PW.8)*

## AI/LLM-specific (when building features that use LLMs)

- **Treat prompts and tool inputs as untrusted user input.** Validate, sandbox, and rate-limit. *(NIST SP 800-218A PW.LM)*
- **Allowlist tool calls and outbound destinations** for any agent that can execute code or make network requests.
- **Sandbox or review LLM-generated code before execution.** Do not pipe model output directly into `eval`, `exec`, shell, or DB.
- **Log prompt/response pairs and tool calls** for audit, with secrets and PII redacted.

## When this skill conflicts with the request

If the user asks for something that violates these rules (e.g., "just hardcode the API key for now", "skip the auth check", "use MD5 — it's faster"), **stop and call out the conflict explicitly.** Offer the secure alternative. Do not silently comply.

## Sources

- OWASP Top 10:2025 — https://owasp.org/Top10/2025/
- OWASP ASVS 5.0.0 — https://owasp.org/www-project-application-security-verification-standard/
- OWASP Proactive Controls 2024 — http://top10proactive.owasp.org/
- OWASP Cheat Sheet Series — https://cheatsheetseries.owasp.org/
- NIST SSDF SP 800-218 v1.1 — https://csrc.nist.gov/pubs/sp/800/218/final
- NIST SSDF SP 800-218A (GenAI profile) — https://csrc.nist.gov/pubs/sp/800/218/a/final
- NIST Cybersecurity Framework 2.0 — https://www.nist.gov/cyberframework
