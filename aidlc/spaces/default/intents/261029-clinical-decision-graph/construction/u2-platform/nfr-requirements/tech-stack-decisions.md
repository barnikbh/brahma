# Tech Stack Decisions — u2-platform

Upstream: `requirements.md` (C-T1, C-T2, FR14, NFR1, NFR9–NFR12), `team-practices.md`, `contract-summary.md` (C2–C4), U2 `functional-spec.md` and `rules.md`. The project's existing `pyproject.toml` already sets Python, Pydantic, pytest, Ruff and mypy.

| Area | Decision | Why |
|---|---|---|
| Language and models | Python 3.12+, Pydantic v2 | Same as U1 and the contracts |
| Storage | SQLite in the shared file, U2-owned tables prefixed `pf_`, its own `pf_connect` with WAL, busy timeout 5 s, foreign keys, autocommit plus explicit `BEGIN IMMEDIATE` | Same pattern as U1; U2 depends on no other unit |
| HTTP client | `httpx` (sync) for Meta and hosted Llama, which expose OpenAI-compatible chat endpoints | One small dependency covers both |
| Claude | `anthropic` SDK | Official client |
| Rate limiting | A small in-process token bucket | No extra service |
| PDF export | `fpdf2` | Pure Python, no system libraries |
| Tests | pytest, pytest-cov; `respx` to fake HTTP; a `recorded` provider reading fixture files | No network in CI |

## Derived Requirements

| ID | Requirement | Source |
|---|---|---|
| NFR1.1 | The gateway adds under 20 ms of overhead per call beyond the provider's own latency (throttle wait excluded) | NFR1 |
| NFR1.2 | `append` and `record_session` each take under 50 ms; `list_sessions` under 200 ms for 1,000 sessions | NFR1 |
| NFR9.1 | U2 line coverage is at least 80% on `brahma.platform`, run in CI with no network | NFR9 |
| NFR10.1 | With `BRAHMA_MODEL_PROVIDER=recorded`, the app starts with no keys, so a judge can run the tests without any account | NFR10 |
| NFR11.1 | One JSON log line per model call: provider, model, purpose, latencyMs, tokens, attempts, error | NFR11 |
| NFR12.1 | Ruff and `mypy --strict` pass on `brahma.platform` | NFR12 |
