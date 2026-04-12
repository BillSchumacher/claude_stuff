# Security Reference

## OWASP Top 10:2025 — code-level checks

| # | Category | What to check |
|---|----------|---------------|
| A01 | Broken Access Control | Auth checked on every endpoint; default-deny; no IDOR via sequential IDs; RBAC enforced server-side |
| A02 | Cryptographic Failures | No MD5/SHA-1/DES/ECB; keys ≥ 256-bit; TLS 1.2+; passwords use memory-hard KDF |
| A03 | Injection | Parameterized queries; no string concat for SQL/commands/LDAP; output context-escaped |
| A04 | Insecure Design | Rate limiting; input length limits; business logic validated; threat model exists |
| A05 | Security Misconfiguration | No default credentials; debug off in prod; CORS restricted; error messages generic |
| A06 | Vulnerable Components | Dependencies pinned and audited; no known CVEs; update policy defined |
| A07 | Auth Failures | Session timeout; password policy; constant-time comparison; credential stuffing protections |
| A08 | Data Integrity Failures | CI/CD pipeline verified; dependencies signed; deserialization restricted to safe formats |
| A09 | Logging Failures | Security events logged; no PII/secrets in logs; log injection prevented; tamper-evident |
| A10 | SSRF | URL scheme allowlisted; internal IPs blocked; redirect targets validated |

## CWE Top 25 — most critical

| CWE | Name | Code-level flag |
|-----|------|----------------|
| 79 | XSS | Raw user content rendered in HTML without escaping |
| 89 | SQL Injection | String concatenation/interpolation in SQL query |
| 78 | OS Command Injection | Shell exec with user input; must use argv array |
| 416 | Use After Free | Manual memory without RAII/smart pointers |
| 20 | Improper Input Validation | Missing validation at trust boundary |
| 125/787 | Out-of-bounds R/W | Array access without bounds check |
| 862 | Missing Authorization | Endpoint/resource lacks auth check |
| 434 | Unrestricted Upload | File type not validated server-side |
| 502 | Unsafe Deserialization | Untrusted data with pickle/ObjectInputStream; use JSON/protobuf |
| 798 | Hardcoded Credentials | Secrets in source; must use env vars or secret manager |
| 306 | Missing Auth for Critical Function | Admin/destructive actions without re-authentication |
| 918 | SSRF | User-controlled URL fetched server-side without allowlist |

## Password hashing (OWASP ASVS V6 · NIST SP 800-63B)

| Algorithm | Status | Notes |
|-----------|--------|-------|
| argon2id | **Preferred** | Memory-hard + time-hard + side-channel resistant |
| bcrypt | Acceptable | 72-byte max input; widely supported |
| scrypt | Acceptable | Memory-hard; less tunable than argon2id |
| PBKDF2-HMAC-SHA256 | Acceptable | NIST-approved; use ≥ 600,000 iterations |
| SHA-256/512 alone | **Reject** | Not a KDF; no work factor |
| MD5, SHA-1 | **Reject** | Broken; never for any security purpose |

## Cryptographic primitives (NIST SP 800-175B · SP 800-57)

| Purpose | Recommended | Reject |
|---------|-------------|--------|
| Symmetric encryption | AES-256-GCM, ChaCha20-Poly1305 | DES, 3DES, AES-ECB, RC4, Blowfish |
| Hashing (non-password) | SHA-256, SHA-3, BLAKE3 | MD5, SHA-1 |
| Key exchange | X25519, ECDH P-256/P-384 | RSA < 2048-bit, DH < 2048-bit |
| Digital signatures | Ed25519, ECDSA P-256 | RSA-1024, DSA |
| Randomness | CSPRNG: os.urandom, crypto.randomBytes, getrandom, /dev/urandom | Math.random, rand(), mt_rand, srand |

## Injection prevention by language

| Language | SQL | Command | XSS |
|----------|-----|---------|-----|
| Python | Parameterized cursor.execute(sql, params) | subprocess.run([...], no shell=True) | Jinja2 autoescaping |
| JavaScript | Parameterized queries (pg, mysql2) | child_process.execFile/spawn, not exec | Framework escaping (React JSX, template literals) |
| PHP | PDO prepared statements | proc_open with argv array | htmlspecialchars(ENT_QUOTES) |
| Go | database/sql with ? placeholders | exec.Command(prog, args...) | html/template auto-escaping |
| Java | PreparedStatement | ProcessBuilder, not Runtime.exec(String) | OWASP Java Encoder |
| C# | SqlCommand with @params | Process.Start with ArgumentList | Razor auto-encoding |
| Rust | sqlx/diesel with bind params | std::process::Command | askama/tera auto-escaping |
