# Code Generation Plan — u5-knowledge-updates

## Summary

- **Builds:** the knowledge-updates library and its C9 API:
  - doctor proposals, with a before-and-after view
  - publish and reject by the reviewer, written to the audit, with a new pack version on publish
  - version history
  - safe source fetching (http(s) only, no local or private addresses, 10 MB / 20 s limits)
  - the "possible verbatim copy" flag, which blocks publishing
  - drafting from a source through the model gateway
  - the background source checker, run as a command or on a daily interval
- **Touches:** `src/brahma/updates/`, `tests/updates/`, `pyproject.toml` (adds `fastapi` as the first web dependency), and U5's steps in `.github/workflows/ci.yml`.
- **Tests:** about 40 pytest tests across 6 components, with no network access (respx, a fake resolver, and the recorded model provider). Line coverage on `brahma.updates` must reach 80%.

Upstream: `functional-spec.md`, `rules.md`, `entities.md`, `security-requirements.md`, `tech-stack-decisions.md`, `security-design.md`, `logical-components.md` and `cicd-pipeline.md` (all U5), plus `contract-summary.md` (C1, C2, C3, C4, C7, C9), `unit-of-work.md` and `requirements.md`.

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

These layers apply to U5: data model and database, repository, business logic, and API (the C9 router). U5 has no frontend.

## Steps

### Skeleton and runner

- [x] **Step 1 — Package and dependency.**
  - Create `src/brahma/updates/__init__.py`.
  - Add `fastapi` to `dependencies` in `pyproject.toml`.
  - Run `.venv/bin/pip install -e ".[dev]"`.
  - *(Setup)*
- [x] **Step 2 — Test runner.** Add `tests/updates/conftest.py` with these fixtures:
  - a temporary database
  - `KnowledgeService` with the IBD pack loaded
  - Audit and Identity services, with the seeded reviewer and doctor profiles
  - a fake resolver
  - a respx router
  - the recorded-provider fixture `tests/updates/fixtures/recorded/draft_proposal/`

### Data model and database

- [x] **Step 3 — Models, errors and `up_connect`.**
  - Models: Proposal, ProposalChange, LinkedSource, SourceCheckRun, DraftedChanges (`extra="forbid"`) and VersionHistoryEntry.
  - Errors: ProposalNotFound, ProposalClosed, CopyFlagged, SourceFetchError and DraftFailed, each with a `log_label`.
  - `up_connect` is `pf_connect` plus the `up_proposal`, `up_proposal_change`, `up_linked_source` and `up_source_check_run` tables.
  - *(US8.1)*
- [x] **Step 4 — Test the models and database (about 5 tests).**
  - Creating the schema twice works (it is idempotent).
  - DraftedChanges rejects extra fields.
  - Proposal status values are checked.

### Repository

- [x] **Step 5 — `UpdateRepository`.** Parameterised SQL to:
  - insert a proposal with its changes
  - get a proposal, and list proposals by pack and status
  - set a proposal's status
  - upsert a linked source and update its hash and status
  - insert a check run
  - *(US8.1, US8.2)*
- [x] **Step 6 — Test the repository (about 5 tests).**
  - A proposal round-trips with its changes.
  - Listing filters work.
  - A status change on a closed proposal raises ProposalClosed.

### Business logic

- [x] **Step 7 — `fetch.py` (BR2.1, BR2.2): SafeFetcher.**
  - Allows only the http and https schemes.
  - Every resolved address must be public, checked with `ipaddress`.
  - Follows at most 3 redirects, checking each one.
  - Streams the body with a 10 MB cap and a 20 s timeout.
  - Converts HTML to text with `html.parser`.
  - The resolver and client are injectable.
  - *(AC8.1.3)*
- [x] **Step 8 — `copycheck.py` (BR2.3, BR2.4).**
  - Detects 26-word overlaps between a draft and its source.
  - Picks the source passage that overlaps the change best.
  - *(AC8.1.2, AC8.2.1)*
- [x] **Step 9 — `drafter.py` (BR3).**
  - Makes a C4 structured call with purpose `draft_proposal`.
  - The source text is placed inside `<source_data>`.
  - A node ID that doesn't exist is rejected.
  - Drafts are dry-run validated with U1's validator.
  - *(AC8.1.2)*
- [x] **Step 10 — `service.py`: UpdateService.**
  - `create_proposal`.
  - `draft_from_source`.
  - `get_proposal`.
  - `publish`, which:
    - checks the role
    - blocks publishing when a copy flag is set
    - re-bases onto the live version if needed
    - calls C1 `create_version`
    - writes the audit record
  - `reject`, which writes the audit record.
  - `version_history`.
  - `check_sources`, which keeps going when a source fails and records a run.
  - Add `check.py` for the CLI and the `BRAHMA_SOURCE_CHECK_HOURS` setting (default 24, 0 means off).
  - *(US8.1, US8.2, US8.3: AC8.1.1, AC8.2.2, AC8.2.3, AC8.3.1, AC8.3.2)*
- [x] **Step 11 — Test the business logic (about 20 tests).**
  - *Fetch refusals:*
    - an `ftp:` URL
    - `http://127.0.0.1`
    - a host that resolves to `10.0.0.5`
    - a redirect to a private address
    - a body over 10 MB
    - a timeout
  - *Fetch success:* HTML is converted to text.
  - *Copy check:*
    - 26 copied words are flagged
    - 25 are not
    - punctuation and case are ignored
  - *Drafter:*
    - a recorded draft builds a proposal
    - an unknown node ID is rejected
    - a model failure stores nothing
  - *Service:*
    - a proposal shows the right before and after values
    - a non-reviewer gets Forbidden on publish
    - a flagged proposal gets CopyFlagged
    - publishing bumps the version, new sessions see the new version and past versions are kept
    - the audit has the published and rejected rows
    - history merges live, superseded, proposed and rejected entries
    - `check_sources` drafts a proposal when a source changes, skips an unreachable source, and records the run

### API

- [x] **Step 12 — `api.py`.**
  - A FastAPI `router` and a `feature` entry for the C7 convention.
  - A `get_update_service` dependency and an `X-Brahma-Profile` profile dependency.
  - C9 endpoints: list and create proposals, get a proposal, publish, reject, and list versions.
  - An exception handler that maps errors to 404, 409, 403, 422 and 502, each with a plain message.
  - *(C9)*
- [x] **Step 13 — Test the API (about 7 tests, using TestClient).**
  - Creating and getting a proposal round-trips.
  - Publishing as a doctor returns 403.
  - Publishing a flagged proposal returns 409.
  - Publishing as the reviewer returns 200.
  - A refused URL returns 422.
  - The versions list works.
  - An unknown proposal returns 404.

### Build configuration and documentation

- [x] **Step 14 — CI.** Add `mypy --strict src/brahma/updates` and `pytest tests/updates --cov=brahma.updates --cov-fail-under=80` to `.github/workflows/ci.yml`. Add `BRAHMA_SOURCE_CHECK_HOURS` to `.env.example` with an empty value.
- [x] **Step 15 — Documentation and traceability.** Write docstrings for the public methods. The orchestrator writes `code-summary.md`, `traceability.json` and `source-manifest.json`.

## Story-to-Step Traceability

| Story / AC | Steps |
|---|---|
| US8.1 (AC8.1.1, AC8.1.2, AC8.1.3) | 3, 5, 7, 8, 9, 10, 11, 12, 13 |
| US8.2 (AC8.2.1, AC8.2.2, AC8.2.3) | 8, 10, 11, 12, 13 |
| US8.3 (AC8.3.1, AC8.3.2) | 10, 11 |
