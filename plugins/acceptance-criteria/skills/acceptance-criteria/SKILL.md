---
name: acceptance-criteria
description: Use at the start of any non-trivial feature, bug fix, or change request — before writing tests or implementation. Forces explicit requirements specification, Given/When/Then acceptance criteria, numeric non-functional requirements, edge-case enumeration, and assumption disclosure following ISO/IEC/IEEE 29148 and BDD practices.
---

# Requirements & Acceptance Criteria

Before writing tests, before writing code, specify what is being built. This skill complements `dev-workflow` (which handles TDD execution): this one forces clarity on **what** is being built; that one handles **how** to build it test-first.

## Required output structure

For every non-trivial task, produce these sections **before any code or test**:

### 1. Requirements (numbered, "shall", testable)

Restate the request as numbered functional requirements. Each one:
- Uses **"shall"** (not "should", not "could", not "will")
- Is **singular** — one shall per statement
- Is **verifiable** — a tester can determine pass/fail without judgment
- Is **unambiguous** — no "fast", "user-friendly", "robust", "appropriate"

Example:
```
R1. The system shall accept CSV files up to 50 MB.
R2. The system shall reject files exceeding 50 MB with a 413 status.
R3. The system shall return the row count within 5 seconds for files up to 50 MB at p99.
```

### 2. Acceptance Criteria (Given/When/Then)

For each user-visible behavior, write at least one Given/When/Then scenario. Cover happy path **and** edge cases / negative paths:

```
Scenario: Successful upload of valid CSV
  Given a CSV file with 1,000 valid rows
  When the user POSTs it to /imports
  Then the response is 202 Accepted
  And the response body contains an import ID

Scenario: Upload exceeding size limit
  Given a CSV file of 60 MB
  When the user POSTs it to /imports
  Then the response is 413 Payload Too Large
  And no rows are persisted
```

### 3. Non-Functional Requirements (numeric)

State NFRs with **numbers**, not adjectives:
- Latency: "p99 < 200 ms under 100 RPS"
- Throughput: "≥ 500 imports/minute sustained"
- Availability: "99.9% over 28-day rolling window"
- Data retention: "imports retained 90 days, then purged"
- Security: "PII fields masked in logs"

Forbidden words for NFRs: *fast, slow, performant, robust, scalable, secure, user-friendly, intuitive, lightweight, lots of, many, few*. Replace each with a number or remove.

### 4. Assumptions and Out of Scope

List explicit assumptions you are making and items you are deliberately not addressing. This invites the user to challenge them before implementation begins:

```
Assumptions:
- CSV files are UTF-8 encoded
- Schema is fixed at: id, name, email
- Authentication is handled by upstream gateway

Out of scope:
- XLSX support (will require a separate ticket)
- Schema discovery / dynamic column mapping
- Backfill of historical files
```

## Edge cases — enumerate them

For every behavior, explicitly enumerate the edge cases as their own scenarios:
- Empty input
- Maximum-size input
- Concurrent modification (two users submit at once)
- Authentication failure
- Authorization failure (correct user, wrong resource)
- Rate limit hit
- Downstream service timeout
- Malformed input
- Unicode / encoding edge cases

## Ask, don't guess

If the request is ambiguous or underspecified on a load-bearing detail (e.g., "schedule reports" without specifying frequency, format, recipients, retention), **ask before coding**. Do not silently choose.

## When this skill conflicts with the request

If asked to skip the spec ("just code it", "no need for requirements, it's small"), explain that the spec catches misunderstandings cheaper than rework. For genuinely trivial changes (typo fixes, single-line updates), this skill does not apply.

## Sources

- ISO/IEC/IEEE 29148:2018 — Requirements engineering — https://www.iso.org/standard/72089.html
- BDD / Cucumber Given-When-Then — https://cucumber.io/docs/bdd/
- ISO/IEC 25010:2023 — Software quality model (NFR categories) — https://www.iso.org/standard/78176.html
