# Code Generation Plan — u4-grounded-agent

## Summary

- **Builds:** the grounded agent and the backend server.
  - The grounding guard checks every claim in a line against the cited nodes. A line with a wrong dose or no node is never shown.
  - The graph walk is deterministic. It extracts findings, confirms them, asks for more data if needed, writes each section from the walked nodes, adds the "why", handles out-of-knowledge, explore and re-walk, and can retry after an error.
  - The local FastAPI server streams the walk as Server-Sent Events. It also covers sign-in, patients and cases, the map, node detail, history and export, health, and mounting the feature modules.
- **Touches:** `src/brahma/agent/`, `src/brahma/server/`, `tests/agent/`, `tests/server/`, `pyproject.toml` (adds `uvicorn`), `.env.example` (server variables), and U4's steps in `.github/workflows/ci.yml`.
- **Tests:** about 55 pytest tests across 7 components, using the recorded model provider. They include the demo-walk acceptance test and the deliberately wrong citation. Line coverage must reach 80% on `brahma.agent` and `brahma.server`.

Upstream: all U4 design files (functional design, NFR requirements, NFR design, infrastructure design), `contract-summary.md` (C1–C8), `unit-of-work.md` and `requirements.md`.

## Testing Contract

```json
{
  "version": 1,
  "methodology": "test-after",
  "source": "team",
  "ordering": "implement each layer, then write and run that layer's tests before committing it to main.",
  "scope": "mvp",
  "test_strategy": "standard",
  "project_type": "greenfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. The specific\nmethodology (TDD, BDD, ATDD, or classic test-after) is affirmed at\npractices-discovery and recorded in `team.md` under this heading with explicit\n`Methodology` and `Ordering` fields; Code Generation resolves those fields\nindependently from coverage, tooling, and scope notes.\n\nWhen no posture has been affirmed, our default per scope is:\n- **Methodology**: test-after\n- **Ordering**: implement each applicable testable layer, then write and run\n  that layer's tests.\n- `mvp`, `enterprise`, `feature`, `infra`, `classic` add an 80% line-coverage\n  floor and CI execution before merge.\n- `bugfix`, `security-patch` add a targeted regression for the specific\n  bug/vulnerability and require the existing suite to remain green.\n- `express` uses the Minimal strategy: requirement-driven unit tests (one per\n  requirement, with a happy-path floor per component); existing tests remain\n  green.\n- `poc`, `refactor`, `workshop` add no extra new-test floor and require the\n  existing suite to remain green.\n\nThe active `Test Strategy` still applies in every scope and determines test\nvolume/types. Scope floors are additive; they never reduce or replace the\nselected strategy.\n\nBuild and Test verifies defined coverage floors and affirmed quality targets;\nthey may not be weakened to make a step pass.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "- **Methodology**: test-after\n- **Methodology evidence**: The builder chose test-after (Q3, option A): build each layer, then write and run its tests. This matches the `org.md` default for a project with no affirmed posture. It keeps evening sessions moving while still producing tests in every piece of work.\n- **Ordering**: implement each layer, then write and run that layer's tests before committing it to main.\n- Coverage: 80% line coverage, measured separately for the Python backend and the TypeScript/React frontend. This is the `mvp` scope floor and is not lowered. (Q4)\n- The checks run automatically in CI (GitHub Actions on the public repo) on every push to `main`: lint, tests, and both coverage floors. (Q4, Q6, Q8)\n- End-to-end: a browser smoke test walks the demo case (sign-in, question, cited answer with the disclaimer, audit record) against the app running locally. There is no hosted URL to test against. (Q4, Q8)\n- Tooling: pytest with pytest-cov for the backend and agent; Vitest with React Testing Library for the frontend; Playwright for the browser smoke test.\n- Model calls are stubbed with recorded responses in unit tests and CI, so the public repo's CI needs no API keys and no network calls to a model provider.\n- The ~20-case synthetic benchmark (pass = at least 95% of recommendations trace to a node and source) is a product deliverable run on demand against the real model, not part of the CI suite.\n- The active Test Strategy (`Standard`) still sets test volume and types. Nothing here reduces it."
    }
  ],
  "obligations": {
    "strategy": "standard",
    "strategy_volume": [
      "Five to eight tests per component.",
      "Unit tests plus integration tests for key boundaries.",
      "Add E2E, performance, or security tests when requirements demand them."
    ],
    "scope_floor": [
      "Meet an 80% line-coverage floor.",
      "Run the selected tests in CI before merge."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "test-after",
    "runner_step": "Bootstrap the minimal test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Bootstrap the minimal test runner/configuration and record the exact unit-scoped command.",
      "Data model / database behavior - implement.",
      "Data model / database behavior - write and run its tests after implementation.",
      "Repository / data access - implement.",
      "Repository / data access - write and run its tests after implementation.",
      "Business logic - implement.",
      "Business logic - write and run its tests after implementation.",
      "API / endpoint - implement.",
      "API / endpoint - write and run its tests after implementation.",
      "Frontend behavior - implement.",
      "Frontend behavior - write and run its tests after implementation.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:d2d883206befa750f058c121aef5c0b1a58dc1d61c232cc814ac34dbf777b3b0",
  "contract_sha256": "sha256:01fe6c10e64168d05471d1404c653dcfd2071927106719976c289d0c23dbfa22"
}
```

The layers that apply to U4 are the data model and database, the repository, business logic (the guard, traversal and engine) and the API (the C8 server). U4 has no frontend.

## Steps

### Skeleton and runner

- [x] **Step 1 — Packages and configuration.**
  - Create `src/brahma/agent/` and `src/brahma/server/`.
  - Add `uvicorn` to the dependencies and run `.venv/bin/pip install -e ".[dev]"`.
  - Add these to `.env.example`, all with empty values: `BRAHMA_SESSION_SECRET`, `BRAHMA_FEATURE_MODULES`, `BRAHMA_LOG_PATH`, `BRAHMA_HOST`, `BRAHMA_PORT`.
  - *(Setup)*
- [x] **Step 2 — Test runner.** Add `tests/agent/conftest.py` and `tests/server/conftest.py` with these fixtures:
  - a temporary database, with the IBD and urology packs loaded
  - all the services
  - the demo patient: synthetic, 34-year-old woman, 58 kg
  - the recorded-provider fixtures under `tests/agent/fixtures/recorded/` for `extract`, `write_section` and `why`, covering the demo walk, a deliberately wrong dose (120 mg) and a urology case
  - a FastAPI `TestClient` that is already signed in

### Data model and database

- [x] **Step 3 — Models, errors, `ag_connect`.**
  - The C6 models, plus Walk, ExploreLane, the WalkEvent types and the form schemas.
  - Errors: WalkNotFound, WalkNotResumable and FindingsNotReady.
  - `ag_walk` and `ag_explore_lane`.
  - *(US3.1–US3.6)*
- [x] **Step 4 — Test the models and database (about 5 tests).**

### Repository

- [x] **Step 5 — `WalkRepository`.** Create, save progress after each section, get, the latest walk per case, and lanes. *(FR5.9)*
- [x] **Step 6 — Test the repository (about 5 tests).** A walk round-trips, resume from the last completed section, and lanes stay separate.

### Business logic

- [x] **Step 7 — `scanner.py` and `guard.py` (BR1).**
  - ClaimScanner: a regex for a number and its unit, plus a vocabulary of names cached per version.
  - `check_line`: declared claims plus scanned claims, matched against C1 `match_claims` and C5 `compute_dose` for doses per kg.
  - `check_line_by_source` (R-03).
  - A guard exception counts as a failed check.
  - *(AC3.2.3, AC7.1.2)*
- [x] **Step 8 — `traverse.py` (BR2.2–BR2.4, BR2.10).**
  - Search across the live packs, then follow edge conditions in order to build the section plan.
  - Return the tests still needed, or out-of-knowledge.
  - *(AC3.2.1, AC3.2.5, AC3.3.1, AC3.3.2, AC3.4.1, AC9.1.1, AC9.1.2)*
- [x] **Step 9 — `writer.py` (BR2.1, BR2.5, BR2.6).** C4 structured calls with data blocks: `extract`, `write_section` and `why`. Add any missing purposes to U2's `Purpose`.
- [x] **Step 10 — `engine.py` and `logging.py`.** WalkEngine is an async event generator. It covers:
  - start → confirm-findings form → paused
  - continue → map_update / line / section_done → needs-data form or why → done → SessionRecord
  - rejected lines → `line_rejected` audit entry and the ungrounded count
  - explore and stop_explore (`explored_not_acted`)
  - rewalk with re-pin
  - error event, then retry
  - free text sent during a walk is queued
  - `run_walk` for U7
  - WalkLogger, which logs only allow-listed fields

  *(US3.1–US3.6, US7.1)*
- [x] **Step 11 — Test the business logic (about 25 tests).**
  - *Guard:*
    - an exact dose passes
    - 120 mg against a node saying 60 mg fails
    - a dose that is scanned but not declared still fails
    - a computed dose per kg passes
    - a line with no cited node fails
    - a guard exception fails the line
    - check_line_by_source passes and fails
  - *Traverse:*
    - the demo findings reach "ulcerative colitis, pancolitis, severe", Tier 2 entry
    - a Crohn's case reaches its subtype
    - missing tests give needs-data
    - a partial answer goes as far as the data allows
    - headache with aura gives out-of-knowledge
    - a urology case uses the urology pack
  - *Engine:*
    - the demo walk gives 0 ungrounded lines and sections in FR4.6 order
    - the wrong citation is not shown, the ungrounded count goes up by one, and the audit has `line_rejected`
    - a timeout mid-stream gives an error event, and retry resumes with no lines sent twice
    - explore leaves the main sections unchanged, and stop writes its audit entry
    - rewalk records both versions
    - the SessionRecord has its fields
    - the log contains no text
    - run_walk works

### API

- [x] **Step 12 — `server/`.**
  - `create_app()` with ServerConfig, SessionMiddleware, the core C8 routes, the SSE walk route (first `progress` event before any model call), the lock check (409), `/api/health`, and C7 mounting with a session-set profile override.
  - `__main__.py` runs uvicorn on 127.0.0.1.
  - On start-up, load packs from `content/` if none are loaded, then seed the profiles.
  - *(C7, C8)*
- [x] **Step 13 — Test the API (about 12 tests).**
  - every route returns 401 when signed out
  - sign-in and the disclaimer
  - create and search patients
  - the case view with the newer-version banner
  - lock: held, and read_only giving 409 on walk
  - the SSE demo walk: progress first, then lines, then done with pack version, provider and the disclaimer
  - node detail with safety
  - a treatment edit
  - session history and export
  - the knowledge feature mounted, with a client-sent profile header ignored
  - health

### Build configuration and documentation

- [x] **Step 14 — CI.**
  - Add the U4 mypy step.
  - Add `pytest tests/agent tests/server -m "not timing" --cov=brahma.agent --cov=brahma.server --cov-fail-under=80`.
- [x] **Step 15 — Documentation and traceability.** Docstrings, plus a short "Run the backend" section in `README.md` (create the file if it doesn't exist). The orchestrator writes `code-summary.md`, `traceability.json` and `source-manifest.json`.

## Story-to-Step Traceability

| Story / AC | Steps |
|---|---|
| US3.1 (AC3.1.1, AC3.1.3) | 9, 10, 11 |
| US3.2 (AC3.2.1–AC3.2.5) | 7, 8, 10, 11, 12, 13 |
| US3.3 (AC3.3.1, AC3.3.2) | 8, 10, 11 |
| US3.4 (AC3.4.1, AC3.4.2) | 8, 10, 11 |
| US3.6 (AC3.6.1, AC3.6.2) | 10, 11 |
| US7.1 (AC7.1.1, AC7.1.2) | 7, 10, 11 |
| US9.1 (AC9.1.1, AC9.1.2) | 8, 11 |
