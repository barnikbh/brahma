# Unit Test Instructions — u5-knowledge-updates

## Framework and Setup

- Uses pytest with pytest-cov, respx for fake HTTP, and FastAPI `TestClient` for the API.
- After Step 1 adds `fastapi`, reinstall with `.venv/bin/pip install -e ".[dev]"`.
- No network access or keys are needed:
  - DNS uses a fake resolver.
  - HTTP goes through respx.
  - The model is the recorded provider (`BRAHMA_MODEL_PROVIDER=recorded`).
  - The database is a temporary SQLite file.

## Run This Unit's Tests

```bash
.venv/bin/python -m pytest tests/updates
```

With coverage:

```bash
.venv/bin/python -m pytest tests/updates --cov=brahma.updates --cov-report=term-missing
```

## Expected Coverage

- **Unit target:** at least 80% line coverage on `brahma.updates`, checked in CI.
- **Project floor:** 80% backend coverage on the full suite, checked at Build and Test.

## Tests Per Component

| Component | File | About |
|---|---|---|
| Models and database | `tests/updates/test_models_db.py` | 5 |
| Repository | `tests/updates/test_repository.py` | 5 |
| Fetch | `tests/updates/test_fetch.py` | 7 |
| Copy check and drafter | `tests/updates/test_copycheck_drafter.py` | 6 |
| Service | `tests/updates/test_service.py` | 10 |
| API | `tests/updates/test_api.py` | 7 |

## Mocking and Test Data

- The source pages are short synthetic HTML written for the tests. They never copy guideline text.
- The recorded draft fixtures are in `tests/updates/fixtures/recorded/draft_proposal/`.
- The profiles are the seeded demo doctor and the clinical reviewer.
