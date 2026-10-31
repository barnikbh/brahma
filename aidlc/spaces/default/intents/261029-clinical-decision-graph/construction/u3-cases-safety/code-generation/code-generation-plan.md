# Code Generation Plan — u3-cases-safety

## Summary

- **Builds:** the cases library:
  - synthetic patients and cases, with search, version pin and re-walk check
  - the chat thread and form drafts
  - finding validation (unit conversion, invalid, conflict, confirm range)
  - the one-tab lock
  - dose computation, and safety checks that say "Not checked" when no node backs them
  - treatment edits, written to the audit
- **Touches:** `src/brahma/cases/` and `tests/cases/`, plus U3's steps in `.github/workflows/ci.yml`. It adds no new dependencies.
- **Tests:** about 35 pytest tests across 5 components, using the real IBD pack (C1) and the real AuditService (C2) on a temporary SQLite file. The floor is 80% line coverage on `brahma.cases`.

Upstream: `functional-spec.md`, `rules.md`, `entities.md` (U3), `security-requirements.md`, `tech-stack-decisions.md`, `security-design.md`, `logical-components.md`, `cicd-pipeline.md` (U3), `contract-summary.md` (C5), `unit-of-work.md`, `requirements.md`.

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

Three layers apply to U3: data model and database, repository, and business logic. U3 has no HTTP routes, because U4 serves them, and it has no frontend.

## Steps

### Skeleton and runner

- [x] **Step 1 — Package.** Create `src/brahma/cases/__init__.py` exporting `CaseService` and the C5 models. *(Setup)*
- [x] **Step 2 — Test runner.** Add `tests/cases/conftest.py`. Its fixtures:
  - a temporary DB
  - `KnowledgeService` with `content/ibd.yaml` loaded
  - `AuditService`
  - `CaseService`
  - a demo patient: 34-year-old woman, 58 kg, penicillin-class allergy, on levothyroxine

### Data model and database

- [x] **Step 3 — Implement the models, errors and `cs_connect`.**
  - Models: Patient, Case, Message, Finding, SafetyResult (its validator rejects `ok` without node IDs), DoseResult, MissingWeight, TreatmentEdit, and PatientChange (`extra="forbid"`, weight between 0 and 400).
  - Errors: CaseNotFound, InvalidPatientChange, NotADrugNode, FormAlreadySubmitted.
  - `cs_connect` creates the `cs_patient`, `cs_case`, `cs_message`, `cs_form_draft`, `cs_finding`, `cs_tab_lock` and `cs_treatment_edit` tables in the shared file, in WAL mode.
  - *(US2.1)*
- [x] **Step 4 — Test the models and database (about 6 tests).**
  - An `ok` SafetyResult with no node is refused.
  - PatientChange rejects unknown fields and a weight of 500 kg.
  - The tables are created idempotently.

### Repository

- [x] **Step 5 — Implement `CaseRepository`.**
  - Parameterised SQL for every entity.
  - Search by case ID, finding name or a diagnosis label in `pathway` messages, limited to the owner's clinic cases.
  - Latest edit per (case, node).
  - Lock upsert with a 45 s expiry.
  - *(US2.1: AC2.1.1)*
- [x] **Step 6 — Test the repository (about 7 tests).**
  - Search finds a case by "calprotectin" and excludes benchmark cases.
  - An empty search returns an empty list.
  - Lock: the same tab gets `held`, a second tab gets `read_only`, and a second tab gets `held` once the lock has expired.
  - Release by a tab that doesn't hold the lock is a no-op.
  - A form draft is saved and then deleted when the form is submitted.

### Business logic

- [x] **Step 7 — Implement `findings.py` (BR2).**
  - Resolve the metric node through the C1 index.
  - Convert units with U1's units.
  - Set `invalid`, `confirm_range` or `conflict` as the rules require.
  - `findings_ready`.
  - *(US3.1: AC3.1.2)*
- [x] **Step 8 — Implement `safety.py` (BR4.1–BR4.3).**
  - `compute_dose`: absolute or per kg, with Decimal rounding and the formula text. With no weight it returns MissingWeight.
  - `safety_checks`: the allergy, pregnancy, interaction and duplicate-class checks. Each is `not_checked` when it has no node.
  - *(US4.1: AC4.1.1–AC4.1.3)*
- [x] **Step 9 — Implement `CaseService` (C5).** It covers:
  - `create_case`, with ID `BR-xxxxxx` and the synthetic flag
  - `search_patients`, `get_case`, `get_patient`
  - `update_patient`, which writes `patient_updated` to the audit in the same transaction
  - `pin` and `newer_version`
  - `append_message`, `list_messages`, `save_form_draft`, `get_form_drafts` and `submit_form`
  - `set_findings`, `set_status` and the lock
  - `compute_dose` and `safety_checks` on the version in effect, with edits applied
  - `apply_edit`: when the drug changes it resets to the new drug's values; it writes `treatment_edited` to the audit and re-runs dose and safety

  *(US2.1, US3.1, US4.1, US4.2: AC2.1.2, AC2.1.3, AC3.1.3, AC4.2.2)*
- [x] **Step 10 — Test the business logic (about 16 tests).**
  - *Findings:* "Hb 102 g/L" becomes 10.2 g/dL with the entered value kept; "high" is `invalid`; a unit that can't be converted is `invalid`; out-of-range is `confirm_range`; two Hb values are `conflict`; and `findings_ready` is false in those cases.
  - *Dose:* a per-kg dose for 58 kg shows its formula; an absolute dose; no weight returns MissingWeight.
  - *Safety:* a penicillin allergy conflicts with a penicillin-class drug and cites the node; a drug with no safety node returns `not_checked` for every check; a duplicate class conflicts.
  - *Service:* `newer_version` returns the newer version after a new version is published; `update_patient` writes its audit entry; an audit failure rolls back the patient change; `apply_edit` records the original, marks the edit and re-runs the checks; a form can't be submitted twice.

### Build configuration and documentation

- [x] **Step 11 — CI.** Add `pytest tests/cases --cov=brahma.cases --cov-fail-under=80` to `.github/workflows/ci.yml`. The repo-wide `mypy --strict src/brahma` already covers this package.
- [x] **Step 12 — Documentation and traceability.** Docstrings on the C5 public methods. The orchestrator writes `code-summary.md`, `traceability.json` and `source-manifest.json`.

## Story-to-Step Traceability

| Story / AC | Steps |
|---|---|
| US2.1 (AC2.1.1, AC2.1.2, AC2.1.3) | 3, 5, 6, 9, 10 |
| US3.1 (AC3.1.2, AC3.1.3) | 7, 9, 10 |
| US4.1 (AC4.1.1, AC4.1.2, AC4.1.3) | 8, 10 |
| US4.2 (AC4.2.2) | 9, 10 |
