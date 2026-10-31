# Code Generation Plan — u2-platform

## Summary

- Builds: the platform library: append-only audit with history and JSON/PDF export, demo profiles with roles and the disclaimer, and the model gateway (Meta, Claude, hosted Llama and a recorded test provider) with throttling, bounded retries, schema checks and call logging
- Touches: `src/brahma/platform/`, `tests/platform/`, `pyproject.toml` (new runtime and test dependencies), `.env.example`, `scripts/check_env_example.py`, `scripts/check_secrets.py`, `assets/fonts/`, `.github/workflows/ci.yml` (adds U2 steps)
- Tests: about 45 pytest tests across 7 components (unit tests plus integration tests for the database and the HTTP boundary with a faked provider), 80% line coverage on `brahma.platform`

Upstream: `functional-spec.md`, `rules.md`, `entities.md` (U2 functional design), `security-requirements.md` and `tech-stack-decisions.md` (U2 NFR requirements), `security-design.md` and `logical-components.md` (U2 NFR design), `cicd-pipeline.md` (U2), `contract-summary.md` (C2, C3, C4, updated), `unit-of-work.md`, `requirements.md`.

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

Applicable layers for U2: data model / database, repository, and business logic. The "API / endpoint" layer for U2 is the outbound provider HTTP boundary, so it is planned as the provider-adapter layer with faked-HTTP tests. U2 has no inbound HTTP routes (U4 serves them) and no frontend.

## Steps

### Skeleton and runner

- [x] **Step 1 — Package and configuration.**
  - Create `src/brahma/platform/__init__.py` with `audit/`, `identity/`, `models/` and `db.py`.
  - In `pyproject.toml`:
    - Add the runtime dependencies `httpx`, `anthropic` and `fpdf2` to `dependencies`, not to `[dev]` (CI review).
    - Add `respx` to `[dev]`.
    - Register the `timing` marker.
  - Bundle `assets/fonts/DejaVuSans.ttf` with its licence in `assets/fonts/LICENSE`.
  - Add `.env.example` listing every U2 variable with empty values: `BRAHMA_MODEL_PROVIDER`, `BRAHMA_MODEL_NAME`, `META_API_KEY`, `ANTHROPIC_API_KEY`, `LLAMA_API_KEY`, `BRAHMA_MODEL_BASE_URL`, `BRAHMA_MODEL_RPM`, `BRAHMA_MODEL_TIMEOUT_S`, `BRAHMA_DB_PATH`.

  *(Setup)*
- [x] **Step 2 — Test runner.**
  - Add `tests/platform/conftest.py` with a temporary-database fixture, the `recorded` provider fixture directory `tests/platform/fixtures/recorded/`, and a respx fake-HTTP fixture.
  - Record the command in `unit-test-instructions.md` and check that it runs with zero tests collected.

### Data model and database

- [x] **Step 3 — Implement models, errors and `pf_connect`.**
  - Pydantic models: AuditEntryIn, SessionRecordIn (with profileId, packVersion, provider and model; C2 updated), Profile, DisclaimerAcceptance, ProviderConfig (key as SecretStr), ModelRequest, ModelResponse.
  - Typed errors: AuditImmutable, AuditInvalid, SessionNotFound, ExportFailed, ProfileNotFound, Forbidden, ConfigError, ModelTimeout, ModelRateLimited, ModelAuthError, ModelUnavailable.
  - `pf_connect`:
    - opens with `isolation_level=None`, WAL, busy timeout and foreign keys
    - creates the `pf_profile`, `pf_disclaimer_acceptance`, `pf_audit_entry`, `pf_session_record` and `pf_model_call_log` tables (NFR design review)
    - adds BEFORE UPDATE and BEFORE DELETE abort triggers on the audit tables and the call log
    - checks the triggers exist on open and recreates any that are missing
    - adds indexes on `created_at` and `case_id`

  *(US7.1)*
- [x] **Step 4 — Test models and database (about 8 tests).**
  - Update and delete are refused on each append-only table.
  - A dropped trigger is restored on reopen.
  - Model validation covers a missing profile, a missing model and a payload over 256 KB.
  - SecretStr never shows the key in `repr`.

### Repository

- [x] **Step 5 — Implement the repositories.**
  - `ProfileRepository`: idempotent seeding of the 3 listed profiles plus the unlisted Benchmark runner; get and list.
  - `AuditRepository`: `BEGIN IMMEDIATE` inserts; queries for the list (text, outcome, includeBenchmark, benchmarkRunId), the detail and the entries by session.
  - `DisclaimerRepository`.

  *(US1.1, US1.2, US7.1, US7.2)*
- [x] **Step 6 — Test the repositories (about 7 tests).**
  - Seeding twice adds no duplicates.
  - The history filters work, and benchmark sessions are hidden by default and shown on request.
  - A failure mid-transaction rolls back.
  - Timing (`timing` marker): append and record under 50 ms, and listing 1,000 sessions under 200 ms.

### Business logic

- [x] **Step 7 — Implement `AuditService` and `PdfExporter`.**
  - `AuditService` covers C2: `append`, `record_session` (which writes the record plus a `session_recorded` entry in one transaction), `list_sessions`, `get_session` and `export_session`.
  - JSON export.
  - The PDF uses DejaVu Sans, with the header "Decision support, not diagnosis · Synthetic patient". Any failure raises ExportFailed and returns nothing partial.

  *(US7.1, US7.2: AC7.1.1, AC7.1.3, AC7.2.1, AC7.2.3)*
- [x] **Step 8 — Implement `IdentityService`.** Covers C3:
  - `list_profiles` and `get_profile`.
  - `needs_disclaimer(profileId, disclaimerVersion, packVersions)`, which compares the major version of each pack, parsed from strings such as "IBD 1.3; URO 0.1".
  - `accept_disclaimer`, which also writes the `disclaimer_accepted` audit entry.
  - `require_role`.

  *(US1.1, US1.2: AC1.1.1, AC1.2.2)*
- [x] **Step 9 — Test the audit and identity services (about 12 tests).**
  - `record_session` writes both rows.
  - Export works as JSON and as PDF, including µ and ≥ and both header strings.
  - An unknown session raises SessionNotFound.
  - A PDF failure raises ExportFailed.
  - `needs_disclaimer` returns true for a new profile, false after acceptance, true after a major version bump or a pack being added, and false after a minor bump.
  - `require_role` refuses the wrong role.

### Provider boundary and gateway

- [x] **Step 10 — Implement `ProviderConfig.from_env`, `TokenBucket` and the adapters.**
  - `ProviderConfig.from_env` checks HTTPS and names the missing variable without its value.
  - `TokenBucket` is thread-safe, with a lock (NFR design review).
  - Adapters:
    - `MetaAdapter` and `LlamaHostedAdapter`: OpenAI-compatible chat completions over httpx.
    - `ClaudeAdapter`: the anthropic SDK.
    - `RecordedAdapter`: reads JSON fixtures keyed by purpose and request hash, with a default fixture per purpose.

  *(FR14)*
- [x] **Step 11 — Implement `ModelGateway.complete`.**
  - Takes a throttle token, sets a timeout, and retries at most twice with 1 s then 3 s backoff.
  - Honours Retry-After up to 10 s. Above that it raises `ModelRateLimited(retryable=True)` (NFR design review).
  - 401 and 403 are not retried.
  - Structured output is validated with Pydantic. A validation failure uses up a retry.
  - In a `finally` block it logs one JSON line (metadata only) and inserts one `pf_model_call_log` row. The `error` value is limited to the error class plus the HTTP status.

  *(US3.4: AC3.4.2)*
- [x] **Step 12 — Test the gateway and adapters (about 12 tests, respx).**
  - *Retries and failures:*
    - a timeout followed by success
    - a 429 followed by success
    - three 500s raise ModelUnavailable
    - a 401 is not retried
    - a Retry-After of 30 raises ModelRateLimited without waiting
  - *Structured output:* invalid JSON followed by valid JSON succeeds; three invalid responses raise.
  - *Config:* an `http://` base URL fails; a missing key names only the variable.
  - *Logging:*
    - Logs and call-log rows contain no key or message text, after both a successful call and a failing call whose body echoes the key.
    - One log line and one call-log row are written per call.
  - *Concurrency and timing:*
    - Concurrent token takes respect the rate.
    - Timing (`timing` marker): recorded-provider overhead under 20 ms.
    - Start-up with `BRAHMA_MODEL_PROVIDER=recorded` works with an empty environment.

### Build configuration and documentation

- [x] **Step 13 — Scripts.**
  - `scripts/check_env_example.py` fails if any variable U2 reads is missing from `.env.example`, or if any value is non-empty (CI review).
  - `scripts/check_secrets.py` scans tracked text files for key patterns: `sk-ant-`, `sk-`, `gsk_` and long base64 strings after `KEY=` (CI review).
  - Both have tests.
- [x] **Step 14 — CI workflow additions to `.github/workflows/ci.yml`.**
  - Set `BRAHMA_MODEL_PROVIDER=recorded`.
  - Run `mypy --strict src/brahma/platform`.
  - Run `pytest tests/platform -m "not timing" --cov=brahma.platform --cov-fail-under=80`. Timing tests run locally under the `timing` marker (CI review).
  - Run `python scripts/check_env_example.py` and `python scripts/check_secrets.py`.
  - The existing U1 steps stay unchanged.
- [x] **Step 15 — Documentation and traceability.** Docstrings on the C2, C3 and C4 public functions. Then `code-summary.md`, `traceability.json` and `source-manifest.json` (written by the orchestrator).

## Story-to-Step Traceability

| Story / AC | Steps |
|---|---|
| US1.1 (AC1.1.1) | 5, 8, 9 |
| US1.2 (AC1.2.2) | 5, 8, 9 |
| US3.4 (AC3.4.2) | 10, 11, 12 |
| US7.1 (AC7.1.1, AC7.1.3) | 3, 4, 7, 9 |
| US7.2 (AC7.2.1, AC7.2.3) | 5, 6, 7, 9 |

## Notes Carried From Reviews

- Functional design review:
  - SessionRecordIn and `needs_disclaimer` signatures were updated in C2 and C3.
  - Audit and Identity share an in-U2 `ProfileRepository`.
  - The U4 server writes `sign_in` entries.
  - A failed schema validation counts as one of the 2 retries.
- NFR design review:
  - `pf_model_call_log` table.
  - Retry-After capped at 10 s.
  - Thread-safe token bucket.
- CI review:
  - `.env.example` names check.
  - Runtime dependencies placed correctly.
  - Timing tests run under their marker, locally.
  - Secret-pattern scan.
