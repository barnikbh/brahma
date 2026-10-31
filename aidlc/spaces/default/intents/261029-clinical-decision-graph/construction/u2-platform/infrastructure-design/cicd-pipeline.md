# CI/CD Pipeline — u2-platform

Upstream: `security-design.md` and `logical-components.md` (U2 NFR design), `functional-spec.md` (U2 workflows W1–W5, which the CI tests exercise), `components.md` (Audit, Identity and ModelGateway depend on no other unit, so U2's CI steps need no other unit), `tech-stack-decisions.md` (U2), `team-practices.md` (public repo, commit to `main`, CI on every push, 80% coverage, local only).

There is no deployment. U2 is a library inside the local backend. Delivery means a green CI run on `main`.

## Pipeline Additions

The steps below are added to the existing repo-wide workflow `.github/workflows/ci.yml` (created with U1). That workflow runs on push to `main` with `permissions: contents: read` on Python 3.12.

| # | Step | Command (indicative) | Gate | NFR |
|---|---|---|---|---|
| 1 | Install (shared) | `pip install -e ".[dev]"`, which now includes `httpx`, `anthropic`, `fpdf2` and `respx` | Fails on install error | NFR10.1 |
| 2 | Lint and types | `ruff check .`, `ruff format --check .`, `mypy --strict src/brahma/platform` | Any error fails | NFR12.1 |
| 3 | Tests with coverage | `pytest tests/platform --cov=brahma.platform --cov-fail-under=80` with `BRAHMA_MODEL_PROVIDER=recorded` | Below 80% or any failure fails | NFR9.1, NFR10.1 |
| 4 | `.env.example` check | `python scripts/check_env_example.py` (fails if any value is non-empty) | Fails on a filled value | NFR5.2 |

Step 3 runs every named U2 test from `security-design.md` and `logical-components.md`: key-free logs on success and failure, audit triggers and their self-repair, field validation, role checks, PDF export with Unicode, timeouts and retries against a fake provider, structured-output validation, the HTTPS check, and the timing tests.

## Secrets

CI sets no provider keys. `BRAHMA_MODEL_PROVIDER=recorded` replays fixture responses, so no network call or key is needed (NFR5.1, NFR10.1). Provider keys exist only in your local `.env` (git-ignored).

## Release and Rollback

| Item | Decision |
|---|---|
| Environments | Local only; CI is the only automated environment |
| Release | A commit on `main` with green CI |
| Rollback | Revert the commit. Audit tables are append-only, so a schema change ships as a new migration, never as an edit to existing rows |
