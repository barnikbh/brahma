# CI/CD Pipeline — u5-knowledge-updates

Upstream:
- U5 NFR design: `security-design.md` and `logical-components.md`
- U5 workflows W1–W5: `functional-spec.md`
- `components.md`: KnowledgeUpdates depends on KnowledgeGraph, Audit, Identity and ModelGateway
- `contract-summary.md`: C7 router mount and C9

There is no deployment. U5 is a library plus a router that U4's local server mounts. The scheduler runs inside the local server, or from the command line with `python -m brahma.updates.check`. There is no cloud scheduler.

## Pipeline Additions

| # | Step | Command | Gate | NFR |
|---|---|---|---|---|
| 1 | Install | `pip install -e ".[dev]"`, which now includes `fastapi` | Fails on error | NFR10 |
| 2 | Types | `mypy --strict src/brahma/updates` | Any error fails | NFR12 |
| 3 | Tests with coverage | `pytest tests/updates --cov=brahma.updates --cov-fail-under=80` with `BRAHMA_MODEL_PROVIDER=recorded` | Fails below 80% or on any test failure | NFR7.1, NFR7.2, NFR8.1–NFR8.4 |

The tests make no network calls. HTTP goes through respx, the resolver is faked, and model calls use the recorded provider.
