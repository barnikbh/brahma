# Unit Test Instructions — u1-knowledge-graph

## Framework and Setup

- pytest with pytest-cov, configured in `pyproject.toml`.
- One-time setup from the project root:
  - `python3 -m venv .venv`
  - `.venv/bin/pip install -e ".[dev]"`
  - If Pydantic has no wheel for the local Python, use Python 3.12 for the venv instead.
- No network, API keys or external services are needed. `BRAHMA_DB_PATH` is set to a temporary file by the `tmp_db` fixture in `tests/knowledge/conftest.py`.

## Run This Unit's Tests

Tests only:

```bash
.venv/bin/python -m pytest tests/knowledge
```

Coverage for this unit, as a command of its own:

```bash
.venv/bin/python -m pytest tests/knowledge --cov=brahma.knowledge --cov-report=term-missing
```

Pack validation:

```bash
.venv/bin/python -m brahma.knowledge.validate content/ibd.yaml content/urology.yaml
```

## Expected Coverage

- **Unit target:** at least 80% line coverage on `brahma.knowledge` (U1's own target, tech-stack-decisions.md NFR9.1). CI checks it with `--cov-fail-under=80` scoped to this package.
- **Project floor:** the 80% backend floor from the Testing Contract is measured by Build and Test on the full assembled suite. A unit-scoped run does not judge it.

## Tests Per Component

| Component | File | About |
|---|---|---|
| Models and database | `tests/knowledge/test_models_db.py` | 8 tests |
| Repository and loader | `tests/knowledge/test_repository_loader.py` | 8 tests |
| Validator | `tests/knowledge/test_validator.py` | 7 tests |
| Matcher | `tests/knowledge/test_matcher.py` | 6 tests |
| Index and service | `tests/knowledge/test_service.py` | 8 tests |
| Content and copy check | `tests/knowledge/test_content.py` | 6 tests |
| Timing (marked `timing`) | `tests/knowledge/test_timing.py` | 3 tests |

## Mocking and Test Data

- Nothing is mocked. U1 has no outside dependencies, and SQLite runs against a temporary file per test.
- Small pack fixtures live in `tests/knowledge/fixtures/`: one minimal valid pack, plus one per failure case (sourceless, cross-pack ID, placeholder, alias, unsafe tag, email address, date).
- The 2,000-node timing fixture is generated in code, not committed.
- The real packs `content/ibd.yaml` and `content/urology.yaml` are used by the content tests as integration tests.
