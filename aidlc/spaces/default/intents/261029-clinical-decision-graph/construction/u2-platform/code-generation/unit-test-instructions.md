# Unit Test Instructions — u2-platform

## Framework and Setup

- pytest with pytest-cov, plus respx for faked HTTP, configured in `pyproject.toml`.
- Setup uses the project's existing venv. After this unit adds dependencies, reinstall with `.venv/bin/pip install -e ".[dev]"`.
- No network or keys are needed. Tests set `BRAHMA_MODEL_PROVIDER=recorded` or use respx. The `tmp_db` fixture in `tests/platform/conftest.py` points `BRAHMA_DB_PATH` at a temporary file.

## Run This Unit's Tests

Tests only, excluding timing:

```bash
.venv/bin/python -m pytest tests/platform -m "not timing"
```

Timing tests, run locally:

```bash
.venv/bin/python -m pytest tests/platform -m timing
```

Coverage for this unit, as a command of its own:

```bash
.venv/bin/python -m pytest tests/platform --cov=brahma.platform --cov-report=term-missing
```

## Expected Coverage

- **Unit target:** at least 80% line coverage on `brahma.platform` (U2 tech-stack-decisions.md NFR9.1). CI checks it, scoped to this package.
- **Project floor:** the 80% backend floor from the Testing Contract is measured by Build and Test on the full suite.

## Tests Per Component

| Component | File | About |
|---|---|---|
| Models and database | `tests/platform/test_models_db.py` | 8 |
| Repositories | `tests/platform/test_repositories.py` | 7 |
| Audit and export | `tests/platform/test_audit.py` | 7 |
| Identity | `tests/platform/test_identity.py` | 5 |
| Config, bucket and adapters | `tests/platform/test_config_adapters.py` | 5 |
| Gateway | `tests/platform/test_gateway.py` | 9 |
| Scripts | `tests/platform/test_scripts.py` | 4 |

## Mocking and Test Data

- HTTP to providers is faked with respx. The Claude adapter is tested with a fake client injected into the adapter.
- Recorded fixtures live in `tests/platform/fixtures/recorded/<purpose>/*.json`.
- Synthetic data only: profile names are the demo names, and session payloads are small hand-written JSON.
