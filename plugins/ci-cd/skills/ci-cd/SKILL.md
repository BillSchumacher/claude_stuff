---
name: ci-cd
description: Language-neutral CI/CD pipeline best practices: dependency caching, code coverage, fast feedback, security scanning, reproducible builds
---

# CI/CD Pipeline Best Practices

When generating CI/CD pipelines, GitHub Actions workflows, or build configurations, apply every applicable rule below. These are language-neutral; load a `ci-cd-{language}` skill alongside this one for language-specific tooling.

## Pipeline structure

Order jobs for fast feedback. Run in parallel where there are no dependencies:

```
lint + typecheck + format-check   (~1-2 min, parallel)
              |
         unit tests               (~3-8 min, matrix)
              |
   security scan + coverage       (~2-4 min, parallel)
              |
    build artifacts + SBOM        (~1-3 min)
              |
       deploy staging             (on merge to main, environment protection)
              |
      deploy production           (manual approval or auto-promote)
```

Use `needs:` to express job dependencies; everything else runs in parallel. Set `timeout-minutes:` on every job.

## Dependency caching

1. Always cache the package manager's **download cache**, not installed artifacts (e.g., cache `~/.cache/pip`, not `site-packages`; cache npm's cache dir, not `node_modules`).
2. Cache key **must** include the hash of the lockfile: `key: ${{ runner.os }}-lang-${{ hashFiles('**/lockfile') }}`.
3. Use the setup action's built-in `cache` parameter when available (`actions/setup-node`, `actions/setup-python`, `actions/setup-go`). Fall back to `actions/cache@v4` for tools without built-in support.
4. Always include a `restore-keys` fallback for partial cache hits.

## Code coverage

5. Generate coverage in **every** PR build. Use the language's standard coverage tool (see language-specific skills).
6. Output in a machine-readable format (Cobertura XML, LCOV, or Codecov JSON) for upload.
7. Enforce a minimum threshold (e.g., `--cov-fail-under=80`) as a required check. Fail the build if coverage drops.
8. Upload to a coverage service (Codecov, Coveralls) or use a threshold action. Use `if: always()` on upload steps so they run even if tests fail.

## Fast feedback

9. Run linters and type checks **before** tests — they fail faster.
10. Use `fail-fast: true` (default) in matrix strategies for PR builds. Use `fail-fast: false` for main/release builds to get the full failure picture.
11. Cancel stale PR runs with concurrency:
    ```yaml
    concurrency:
      group: ${{ github.workflow }}-${{ github.head_ref || github.ref }}
      cancel-in-progress: true
    ```
12. Target total pipeline time under 10 minutes. Consider test splitting/sharding for large suites.

## Security scanning

13. **SAST**: Run CodeQL, Semgrep, or SonarQube on every PR. Upload SARIF results to the GitHub Security tab.
14. **Dependency audit**: Run the language-native audit tool (see language-specific skills) plus a cross-language scanner (OSV-Scanner, Trivy, or Grype).
15. **Secret scanning**: Enable GitHub secret scanning. Add `gitleaks` or `trufflehog` as a CI step.
16. **Container scanning**: Run Trivy on Docker images before push.

## Reproducible builds

17. Commit lockfiles to the repository. Use frozen install commands (`--frozen-lockfile`, `--ci`, `--locked`, `--deploy`).
18. Pin runner OS versions: `runs-on: ubuntu-24.04`, not `ubuntu-latest`.
19. Pin language versions explicitly in the workflow.
20. Pin third-party actions to **full-length commit SHAs**, not tags:
    ```yaml
    uses: actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332 # v4.2.2
    ```
21. Use Dependabot or Renovate to auto-update pinned SHAs.

## Minimal permissions

22. Set top-level `permissions: {}` (empty), then grant per-job only what's needed:
    ```yaml
    permissions:
      contents: read
      checks: write
    ```
23. Use OIDC (`id-token: write`) for keyless cloud auth instead of long-lived secrets.
24. Use environment protection rules with required reviewers for deployment jobs.

## Artifact management

25. Tag artifacts with the git commit SHA for traceability.
26. Build once, deploy everywhere — same artifact promoted through environments.
27. Set retention policies on `actions/upload-artifact`. Don't keep PR artifacts indefinitely.

## Supply chain

28. Generate SBOMs in CI (`cdxgen`, `syft`). Attach to releases.
29. Sign artifacts with Sigstore/Cosign for verifiable provenance.

## Sources

- https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows
- https://docs.github.com/en/actions/security-for-github-actions/security-hardening-for-github-actions
- https://owasp.org/www-project-devsecops-guideline/
