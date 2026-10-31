# CI/CD Pipeline — u1-knowledge-graph

Upstream: `security-design.md` and `logical-components.md` (U1 NFR design), `functional-spec.md` (U1 workflows W1–W7, which the CI tests exercise), `components.md` (KnowledgeGraph has no dependencies, so its CI job needs no other unit), `tech-stack-decisions.md` (U1), `team-practices.md` (public GitHub repo, commit to `main`, CI on every push, 80% coverage, Ruff, run locally only, no hosted deploy).

There is no deployment: the app runs locally, and U1 is a library inside the backend. "Delivery" means a green CI run on `main` and, for the submission, a tagged commit.

## Pipeline (GitHub Actions, on every push to `main` and on pull requests)

The repo-wide workflow `.github/workflows/ci.yml` runs one backend job. U1's steps run inside it, in this order:

| # | Step | Command (indicative) | Gate | NFR |
|---|---|---|---|---|
| 1 | Set up Python 3.12 and install dependencies from the lock file | `uv sync --frozen` | Fails on install error | NFR10.1 |
| 2 | Lint and format check | `ruff check . && ruff format --check .` | Any error fails the build | NFR12.1 (Ruff) |
| 3 | Type check | `mypy --strict src/brahma/knowledge` | Any error fails the build | NFR12.2 |
| 4 | Tests with coverage | `pytest tests/knowledge --cov=brahma.knowledge --cov-fail-under=80` | Below 80% or any failure fails the build | NFR9.1 |
| 5 | Pack validation | `python -m brahma.knowledge.validate content/ibd.yaml content/urology.yaml` | Any PackLoadError fails the build | NFR2.1, NFR6.1, NFR8.1 |

The tests in step 4 include U1's named security and performance tests: exact matching, triggers and index, safe loader, patient-data scan, concurrent publish, the 50 ms and 2 s timing tests, and the log-line test (`security-design.md`, `logical-components.md`).

## Secrets

U1 needs none. The CI job sets no API keys; `BRAHMA_DB_PATH` points to a temporary file per test (NFR5.1). The workflow has read-only repository permissions.

## Environments and Release

| Item | Decision |
|---|---|
| Environments | Local only. CI is the only automated environment |
| Release | A commit on `main` with green CI; the commit the demo video uses is tagged (team-practices.md) |
| Rollback | Revert the commit on `main`. Pack content rolls back by publishing a new version or re-loading the previous file with a higher number (BR1.3) |
| Content check | `scripts/check_copy.py` runs on your machine before committing pack changes, because source passages are kept out of the repo (BR3.6). It is a manual pre-commit checklist step, not a CI step |
