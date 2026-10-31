# Unit Test Instructions — u3-cases-safety

## Framework and Setup

- pytest with pytest-cov, already configured in `pyproject.toml`. There are no new dependencies.
- No network or keys are needed. The fixtures in `tests/cases/conftest.py` use a temporary SQLite file, load `content/ibd.yaml` through `KnowledgeService`, and use the real `AuditService`.

## Run This Unit's Tests

```bash
.venv/bin/python -m pytest tests/cases
```

With coverage for this unit:

```bash
.venv/bin/python -m pytest tests/cases --cov=brahma.cases --cov-report=term-missing
```

## Expected Coverage

- **Unit target:** at least 80% line coverage on `brahma.cases`, checked in CI.
- **Project floor:** the 80% backend floor is measured by Build and Test on the full suite.

## Tests Per Component

| Component | File | Tests (approx.) |
|---|---|---|
| Models and database | `tests/cases/test_models_db.py` | 6 |
| Repository and lock | `tests/cases/test_repository.py` | 7 |
| Findings | `tests/cases/test_findings.py` | 6 |
| Dose and safety | `tests/cases/test_safety.py` | 6 |
| Service | `tests/cases/test_service.py` | 8 |

## Mocking and Test Data

- There are no mocks except one, which simulates an audit failure to test rollback.
- Data is synthetic only: the demo patient. Drug and safety nodes come from the IBD pack.
- When a test needs a node shape the pack lacks, for example a drug with no safety nodes, it uses a small inline YAML pack.
