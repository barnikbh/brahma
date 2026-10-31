# Unit Test Instructions — u4-grounded-agent

## Framework and Setup

- Tests use pytest with pytest-cov. The API is tested with FastAPI's `TestClient`.
- After Step 1 adds `uvicorn`, reinstall with `.venv/bin/pip install -e ".[dev]"`.
- No network access or API keys are needed:
  - `BRAHMA_MODEL_PROVIDER=recorded`, with fixtures in `tests/agent/fixtures/recorded/`.
  - A temporary SQLite file, with the IBD and urology packs loaded.
  - A per-test session secret.

## Run This Unit's Tests

```bash
.venv/bin/python -m pytest tests/agent tests/server -m "not timing"
```

With coverage:

```bash
.venv/bin/python -m pytest tests/agent tests/server --cov=brahma.agent --cov=brahma.server --cov-report=term-missing
```

## Expected Coverage

- **Unit target:** at least 80% line coverage on `brahma.agent` and `brahma.server`, checked in CI.
- **Project floor:** 80% backend coverage on the full suite.

## Tests Per Component

| Component | File | About |
|---|---|---|
| Models and database | `tests/agent/test_models_db.py` | 5 |
| Repository | `tests/agent/test_repository.py` | 5 |
| Guard | `tests/agent/test_guard.py` | 8 |
| Traverse | `tests/agent/test_traverse.py` | 7 |
| Engine | `tests/agent/test_engine.py` | 10 |
| Server | `tests/server/test_api.py` | 12 |
| Timing (local) | `tests/agent/test_timing.py` | 2 |

## Mocking and Test Data

- The only stand-in for a model is the recorded provider. A timeout is simulated by a fake adapter that raises U2's `ModelTimeout`.
- All data is synthetic. The demo patient is the 34-year-old woman from AC3.2.1.
- The wrong-citation fixture returns "Methylprednisolone 120 mg" and cites the 60 mg node.
