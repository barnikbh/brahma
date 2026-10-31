# CI/CD Pipeline — u3-cases-safety

Upstream:
- `security-design.md` and `logical-components.md` (U3 NFR design)
- `functional-spec.md` (U3 workflows W1–W7)
- `components.md` (Cases and TreatmentSafety depend on KnowledgeGraph and Audit)
- `contract-summary.md` (C5)

There is no deployment and no new infrastructure. U3 is a library inside the local backend, and it stores its data in the shared SQLite file under the `cs_` tables.

## Pipeline Additions

These steps are added to `.github/workflows/ci.yml`:

| # | Step | Command | Gate | NFR |
|---|---|---|---|---|
| 1 | Lint and types | `mypy --strict src/brahma/cases`, which also runs as part of the repo-wide `src/brahma` | Any error fails | NFR12 |
| 2 | Tests with coverage | `pytest tests/cases --cov=brahma.cases --cov-fail-under=80` | Below 80% or any failure fails | NFR9, NFR6.1, NFR7.1, NFR8.1, NFR8.2 |

The tests use a temporary SQLite file, the real IBD pack loaded through C1, and the real C2 AuditService. No keys are needed (NFR5.1).
