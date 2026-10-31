# Code Generation Plan — u1-knowledge-graph

## Summary

- Builds: the Python knowledge-graph library (load, validate, version, search, traverse, claim matching, comments), the IBD pack v1.0 (UC and Crohn's at full depth) and the urology stub, plus the project's Python and CI skeleton (first unit)
- Touches: `pyproject.toml`, `src/brahma/knowledge/`, `content/`, `scripts/check_copy.py`, `tests/knowledge/`, `.github/workflows/ci.yml`, `.gitignore` (adds `.venv/`, `data/`, `.env`)
- Tests: about 45 pytest tests across 8 components (unit tests plus integration tests for the database boundary and full pack loads), 80% line coverage on `brahma.knowledge`

Upstream: `functional-spec.md`, `rules.md`, `entities.md` (U1 functional design), `security-design.md` and `logical-components.md` (U1 NFR design), `cicd-pipeline.md` (U1), `contract-summary.md` (C1), `unit-of-work.md`, `requirements.md`.

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

Applicable layers for U1: data model / database, repository, business logic. U1 has no API endpoint (U4 serves HTTP) and no frontend (U8), so those layers are omitted.

## Steps

### Project skeleton and runner

- [x] **Step 1 — Project structure and configuration.**
  - `pyproject.toml`: package `brahma`, src layout, `requires-python = ">=3.12"`, runtime dependencies `pydantic>=2`, `pyyaml`, and dev dependencies `pytest`, `pytest-cov`, `ruff`, `mypy`, `types-PyYAML`. Ruff and mypy settings live in the same file.
  - Create `src/brahma/__init__.py` and `src/brahma/knowledge/__init__.py`.
  - Add `.venv/`, `data/`, `.env` and `__pycache__/` to the existing `.gitignore` (your file; this plan changes it, per the workspace rule never to commit `data/` plaintext).
  - Local environment: `python3 -m venv .venv` and `pip install -e ".[dev]"`. This machine has Python 3.15. If Pydantic has no wheel for 3.15, install Python 3.12 with Homebrew (`brew install python@3.12`) and rebuild the venv with it; that is a command for you to approve when it comes up. *(Traces: setup for all stories)*
- [x] **Step 2 — Test runner.** Add the pytest configuration in `pyproject.toml` (`testpaths`, markers `timing`), plus `tests/knowledge/conftest.py` with a temporary-database fixture and small pack fixtures. Record the exact command in `unit-test-instructions.md`. Check that the command runs with zero tests collected.

### Data model and database layer

- [x] **Step 3 — Implement models and the database.**
  - `models.py`: Pydantic models for Pack, PackVersion, Node, the per-type field schemas, Edge, Source, NodeComment, Fact, Step, ChangeSet and Claim, all with `extra="forbid"` (entities.md).
  - `errors.py`: PackLoadError, PackBusy, VersionNotIncreasing, VersionRequired, NodeNotFound, CommentInvalid.
  - `db.py`: `kg_connect(path)` with `isolation_level=None`, WAL, `busy_timeout=5000` and `foreign_keys=ON`. It creates the `kg_` tables, the BEFORE UPDATE and DELETE immutability triggers, the live-to-superseded-only status trigger, and the partial unique index on the live version (security-design.md NFR7.1, NFR8.2). *(US8.2, US3.2)*
- [x] **Step 4 — Test models and the database (about 8 tests).** Cover:
  - required fields per node type
  - `extra` fields rejected
  - pragmas set
  - update and delete refused on each table
  - superseded back to live refused
  - a second live row refused by the index
  - Fact, Step and ChangeSet validation

### Repository layer

- [x] **Step 5 — Implement `repository.py` and `loader.py`.**
  - `KnowledgeRepository`: `BEGIN IMMEDIATE` writes; insert pack, version, nodes, edges and sources; `supersede`; reads by version; `list_versions`; comments.
  - `PackLoader`: 5 MB and extension check, then `NoAliasSafeLoader` (a SafeLoader subclass that refuses aliases).
- [x] **Step 6 — Test the repository and loader (about 8 tests).** Cover:
  - round-trip of a small pack
  - versions listed newest first
  - two concurrent `create_version` calls never leave two live versions
  - an interrupted write leaves the previous version intact
  - each refused input: alias, `!!python/object` tag, a 6 MB file, a `.json` extension
  - comments: blank, 1,001 characters and an unknown node are refused, and markup round-trips unchanged

### Business logic layer

- [x] **Step 7 — Implement `validator.py`.** `PackValidator` enforces:
  - BR1.1: every node has a known source
  - BR1.2: edges are well formed, condition names are known, and IDs carry the pack prefix and are unique
  - BR1.4: required fields per type
  - BR3.5: no `[...]` placeholders in any field
  - the patient-data scan (dates, email addresses, runs of 8 or more digits), with an allow-list for clinical schedules such as "weeks 0, 2, 6" (NFR6.1)

  *(US3.2, US9.1)*
- [x] **Step 8 — Implement `units.py` and `matcher.py`.**
  - `UNIT_TABLE` with Decimal factors, for example Hb g/L to g/dL, and calprotectin mg/kg equal to µg/g.
  - `normalise_text` and synonym resolution.
  - `match_claims` with exact Decimal equality.
  - `find_supporting_node` (BR2.5).

  *(US3.2, AC3.2.3)*
- [x] **Step 9 — Implement `index.py` and `service.py`.**
  - `GraphIndex`, built when a version is loaded or created (not on first call), for name and synonym lookup and adjacency.
  - `search` (BR2.1).
  - `neighbours` returning a Step with status followable, not_taken, alternative or unknown_input (BR2.2, BR2.3).
  - `reference_range` with precedence and widest (BR2.4).
  - `subgraph` (BR2.6).
  - `KnowledgeService`, exposing the full C1 interface: `load_pack`, `create_version`, `live_version`, `list_versions`, `get_node`, `search`, `neighbours`, `reference_range`, `sources`, `match_claims`, `find_supporting_node`, `subgraph`, `list_comments`, `add_comment`. It writes one JSON log line per load or version (NFR11.1).
  - `validate.py` CLI.

  *(US3.2, US3.6, US8.2, US9.1)*
- [x] **Step 10 — Test the business logic (about 20 tests).**
  - *Validator:* a sourceless node, a cross-pack ID, a missing drug field, a placeholder, an email address, a date, and a clinical schedule that must be allowed.
  - *Matcher:* 60 = 60 passes, 60.4 vs 60 fails, 102 g/L = 10.2 g/dL passes, a drug synonym passes, an unknown unit returns `unknown_unit`, a per-kg node with an absolute claim fails.
  - *Search and neighbours:* a symptom synonym matches, a duration below the minimum doesn't, statuses are followable, not_taken, unknown_input and alternative.
  - *Reference range:* female, unknown sex gives the widest range plus the flag.
  - *Service:* re-loading the same version number raises VersionNotIncreasing; `create_version` supersedes the old version; the log line has its fields.
  - *Timing* (marked `timing`): a 2,000-node fixture with search and neighbours under 50 ms, and a cold index build.

### Content

- [x] **Step 11 — Write the IBD pack v1.0 (`content/ibd.yaml`).** Drafted with Claude, paraphrased and cited:
  - UC branch at full depth (BR3.1): findings, IBD, the four tests, extent E1–E3, severity, Tiers 1–3 with entry criteria and drug options, monitoring, diet, watch-outs, surgery triggers.
  - Crohn's branch at the same depth (BR3.2).
  - Infectious-colitis alternative, plus drug, interaction, penicillin-class allergy and response-criterion nodes (BR3.3).
  - Hb reference ranges by sex, and the calprotectin threshold.

  Every dose, frequency and duration comes from the cited guideline. Any value I can't source with confidence is left out of the node, not guessed, and listed in `code-summary.md` for your reviewer. *(US3.2, US3.6, AC3.2.1, AC3.2.5)*
- [x] **Step 12 — Write the urology stub v0.1 (`content/urology.yaml`)**: a handful of cited nodes forming one walkable path (BR3.4). *(US9.1)*
- [x] **Step 13 — `scripts/check_copy.py`**: flags runs of more than 25 words copied from source passages kept outside the repo (BR3.6).
- [x] **Step 14 — Test the content (about 6 tests).**
  - Both packs load cleanly through `validate.py` (pack load is an integration test).
  - The UC demo facts reach pancolitis severe and Tier 2 through `search` and `neighbours` (AC3.2.1 at the U1 level).
  - The Crohn's demo facts reach a Crohn's sub-type (AC3.2.5).
  - The alternative branch is present (AC3.6.1).
  - The urology walk reaches its plan (AC9.1.1).
  - `check_copy` flags a 26-word copied run.
  - Both packs load in under 2 s (NFR10.1).

### Build configuration and documentation

- [x] **Step 15 — CI workflow `.github/workflows/ci.yml`.** Triggered on push to `main`, with `permissions: contents: read`, on Python 3.12. The steps are:
  1. install
  2. Ruff check and format check
  3. `mypy --strict src/brahma/knowledge`
  4. pytest with `--cov=brahma.knowledge --cov-fail-under=80`
  5. pack validation

  The workflow is repo-wide, so later units add their own steps (cicd-pipeline.md).
- [x] **Step 16 — Documentation and traceability.**
  - Docstrings on the C1 public functions.
  - `code-summary.md` listing what was built, how to run it, and the content values left for your reviewer.
  - `traceability.json`.
  - `source-manifest.json`.

## Story-to-Step Traceability

| Story / AC | Steps |
|---|---|
| US3.2 (AC3.2.1, AC3.2.3, AC3.2.5) | 3, 7, 8, 9, 10, 11, 14 |
| US3.6 (AC3.6.1) | 9, 11, 14 |
| US8.2 (AC8.2.2) | 3, 5, 6, 9 |
| US9.1 (AC9.1.1, AC9.1.2) | 7, 9, 12, 14 |

## Notes Carried From Reviews

- `kg_connect` uses `isolation_level=None`, so `BEGIN IMMEDIATE` controls each transaction (NFR design review, minor).
- `GraphIndex` is built at load or version creation, with a cold-build test (NFR design review, minor).
- The patient-data scan has an allow-list and a false-positive test (NFR design review, minor).
- `create_version` requires the base to be the live version, and version numbers compare numerically by major then minor. Edge condition names match by the BR2.1 name rule, and `edgeId` is unique within a version and stable across versions (functional design review, minor).
- The CI trigger is push to `main` only, with read-only permissions. Both pack files are committed in this unit (infrastructure review, minor).
