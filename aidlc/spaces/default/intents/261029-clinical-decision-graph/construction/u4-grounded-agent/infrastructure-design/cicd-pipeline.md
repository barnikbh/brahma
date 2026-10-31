# CI/CD Pipeline — u4-grounded-agent

Upstream: `logical-components.md` and `security-design.md` (U4 NFR design), `functional-spec.md` (U4 workflows W1–W8), `components.md` (GroundedAgent, BackendServer), and `contract-summary.md` (C6, C8).

There is no deployment. Delivery means a green CI run on `main`.

## Pipeline Additions

| # | Step | Command | Gate | NFR |
|---|---|---|---|---|
| 1 | Install | `pip install -e ".[dev]"`, which now includes `uvicorn` | Fails on error | NFR10 |
| 2 | Types | `mypy --strict src/brahma/agent src/brahma/server` | Any error fails | NFR12 |
| 3 | Tests | `pytest tests/agent tests/server -m "not timing" --cov=brahma.agent --cov=brahma.server --cov-fail-under=80` with `BRAHMA_MODEL_PROVIDER=recorded` | Below 80% or any failure fails | NFR2.1, NFR7, NFR8 |

The demo-walk acceptance tests (AC3.2.1, AC3.2.3) run in step 3 on recorded fixtures. Timing tests run locally only.
