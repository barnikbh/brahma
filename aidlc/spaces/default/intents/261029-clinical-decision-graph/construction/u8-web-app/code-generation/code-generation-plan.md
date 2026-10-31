# Code Generation Plan — u8-web-app

## Summary

- **Builds:** the doctor web app.
  - Sign-in and disclaimer, patient search, create and reopen.
  - The consultation workspace: a sticky patient card, chat with checked lines and node chips, chat forms, and the live graph map with light-up, selection sync, explore lane, banners and every walk state.
  - The node panel with dose, safety and edit.
  - History with replay and export.
  - The Knowledge screen (propose, review, publish).
  - The disclaimer and pack version show on every screen.
- **Touches:**
  - `web/`, a new Vite + React + TypeScript app.
  - `src/brahma/server/app.py`, so the server serves `web/dist` at `/`, plus one test for that.
  - The `web` job in `.github/workflows/ci.yml`.
  - `.gitignore`, which adds `web/node_modules` and `web/dist`.
  - The README run steps.
- **Tests:** about 45 Vitest + React Testing Library tests across 7 component groups, with at least 80% line coverage on `web/src`, plus one local Playwright smoke test of the demo walk.

Upstream: all U8 design files, `contract-summary.md` (C8 + R-02, C9), the refined mockups (`mockups.md`, `interaction-spec.md`, `design-system-mapping.md`, `accessibility-checklist.md`) and `requirements.md`.

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

Applicable layers for U8:
- **API access:** the client, the SSE parser and the types. This is U8's data-access layer.
- **Business logic:** the walk reducer and the lock and case hooks.
- **Frontend behaviour:** pages and components.

U8 has no database. The single server change (serving `web/dist`) is covered by a pytest.

## Steps

### Skeleton and runner

- [x] **Step 1 — Scaffold `web/`.** Create the Vite React TypeScript app by hand with these pieces:
  - `package.json` scripts: dev, build, lint, typecheck, test and e2e.
  - Runtime dependencies: react, react-dom, react-router-dom, @xyflow/react, and the Radix primitives shadcn/ui needs, plus class-variance-authority, clsx and tailwind-merge.
  - Dev dependencies: vite, @vitejs/plugin-react, typescript, tailwindcss, postcss, autoprefixer, eslint with typescript-eslint and react plugins, prettier, vitest, @vitest/coverage-v8, jsdom, @testing-library/react, @testing-library/user-event, @testing-library/jest-dom and @playwright/test.
  - Run `npm install` in `web/`.
  - Config: `tsconfig` in strict mode, a Vite proxy for `/api` to 127.0.0.1:8000, Tailwind with the tokens from `design-system-mapping.md`, and ESLint with `react/no-danger` set to error.
  - Add `web/node_modules` and `web/dist` to `.gitignore`.
  - *(Setup)*
- [x] **Step 2 — Test runner.**
  - Vitest with jsdom, a setup file, and an 80% line threshold.
  - A `test/fakeApi.ts` that mocks fetch with C8 and C9 fixtures, including a fake SSE stream of the demo walk.
  - Record the command in the test instructions.

### API access

- [x] **Step 3 — `api/types.ts`, `api/client.ts`, `api/walkStream.ts`.**
  - The C8 and C9 types.
  - A fetch wrapper that:
    - uses `credentials: "same-origin"`
    - parses `{error: {...}}` responses into an `ApiError`
    - sends the `X-Brahma-Tab` header from `sessionStorage`
    - redirects to sign-in on a 401
  - An SSE parser over a `ReadableStream`.
  - *(C8, C9)*
- [x] **Step 4 — Test the API layer (about 6 tests).**
  - Error parsing.
  - The tab header is sent.
  - A 401 redirects.
  - SSE parsing of multi-chunk and multi-line events.
  - Stream errors.

### Business logic

- [x] **Step 5 — `state/walkReducer.ts`, `useCase.ts`, `useLock.ts`.**
  - **Workspace state machine:** empty, confirm, working, needs_data, answered, exploring, edit, out_of_knowledge, error, read_only.
  - **Event handling:** only `line` events add answer text. Map node and edge status updates come from `map_update`. Submitted forms collapse to a one-line summary.
  - **Retry:** sends `continue` with the walkId.
  - **Lock:** a 15 s heartbeat, released on `beforeunload`.
  - *(BR3.1–BR3.9)*
- [x] **Step 6 — Test the business logic (about 10 tests).**
  - The demo event sequence reaches `answered` with lines in the correct sections.
  - A `progress` event never adds answer text.
  - An error keeps the inputs, and retry sends the walkId.
  - Out-of-knowledge state.
  - The explore lane stays separate.
  - The lock returns `read_only`.
  - The heartbeat interval.

### Frontend behaviour

- [x] **Step 7 — Shell, sign-in, disclaimer, patients.**
  - `AppShell`: disclaimer, pack chips, navigation, desktop-only notice, and the "server not running" state.
  - `SignInPage`.
  - `DisclaimerPage`: Accept is disabled until both boxes are ticked.
  - `PatientsPage`: debounced search, status chips, empty state and create; every patient is marked synthetic.
  - *(BR1, BR2)*
- [x] **Step 8 — Workspace.**
  - `WorkspacePage` and `PatientCard`.
  - `ChatThread`, `ChatLine` and `NodeChip`.
  - `ChatForm` variants with the A4 validation states.
  - `WalkSummary`.
  - Banners: newer version, and read-only.
  - `GraphCanvas` on React Flow:
    - fixed columns
    - badges for done ✓, test needed ?, not in pack ⊘ and entry ▶
    - edge styles
    - the explore lane
  - Selection sync, by click and by keyboard.
  - *(BR3)*
- [x] **Step 9 — Node panel, History, Knowledge.**
  - `NodePanel`:
    - dose with its formula
    - `ResultBadge`
    - safety: "! Allergy conflict" or "? Not checked: no grounded safety data"
    - edit, which opens the chat form; edited items show the ✎ marker
  - `HistoryPage` and `SessionDetail`: filters, why chips, read-only replay, and JSON and PDF export.
  - `KnowledgePage` and `ProposalView`:
    - the proposal form, which keeps its input on error
    - before and after, with the passage
    - the copy flag disables Publish
    - Publish and Reject for reviewers
    - version history
  - *(BR4, BR5, BR6)*
- [x] **Step 10 — Test the frontend (about 25 tests).**
  - *Shell, sign-in and patients:*
    - The shell shows the disclaimer and pack chips on every page.
    - Sign-in lands on Patients.
    - Accept is disabled until both boxes are ticked.
    - A search with no results shows "No patients found" and Create.
  - *Workspace:*
    - The demo walk renders the confirm form, the needs-data form, cited lines, and the summary with 0 ungrounded.
    - Selecting a chat line opens the panel, and selecting a node highlights its line.
    - The keyboard works for selection.
    - Results show a symbol and a word, not colour alone.
    - The newer-version banner shows.
    - The read-only banner disables input.
    - The error state offers Retry.
    - Out-of-knowledge shows its message.
  - *Node panel:* shows both the allergy-conflict and not-checked safety states.
  - *History:* the filter's empty state, and replay is read-only.
  - *Knowledge:* the copy flag blocks Publish, a doctor sees no Publish button, and input is kept on error.
  - *XSS:* node text containing `<script>` is rendered as plain text.

### Build configuration and documentation

- [x] **Step 11 — Serve the build from U4.**
  - In `src/brahma/server/app.py`, mount `web/dist` as static files at `/` with an SPA fallback when the folder exists, without shadowing `/api`.
  - Add a pytest in `tests/server/` that checks `/` serves `index.html` from a temporary dist folder, and that `/api/health` still works.
- [x] **Step 12 — Smoke test and CI.**
  - Add `web/e2e/demo.spec.ts`. It signs in as Dr. Maya, accepts the disclaimer, creates a patient, types the demo text, confirms the findings, answers the needs-data forms, and checks for cited lines, the disclaimer and 0 ungrounded. It then checks that History lists the session.
  - It runs locally against `python -m brahma.server` with `BRAHMA_MODEL_PROVIDER=recorded`. Configure it in `playwright.config.ts`, including `webServer`.
  - Add the `web` job to CI: `npm ci`, lint, typecheck, Prettier check, tests with coverage, and build.
- [x] **Step 13 — Documentation and traceability.**
  - Add the README's "Run the app" steps: `cd web && npm ci && npm run build`, then `python -m brahma.server`, then open `http://127.0.0.1:8000`.
  - The orchestrator writes `code-summary.md`, `traceability.json` and `source-manifest.json`.

## Story-to-Step Traceability

| Story / AC | Steps |
|---|---|
| US1.1, US1.2 (AC1.1.1, AC1.1.2, AC1.2.1) | 7, 10 |
| US2.1 (AC2.1.1–AC2.1.3) | 7, 8, 10 |
| US3.1–US3.6 (AC3.1.x–AC3.6.x) | 3, 5, 6, 8, 10, 12 |
| US4.1, US4.2 (AC4.1.x, AC4.2.x) | 9, 10 |
| US7.1, US7.2 (AC7.1.1, AC7.1.2, AC7.2.x) | 9, 10, 12 |
| US8.1, US8.2 (AC8.1.x, AC8.2.x) | 9, 10 |
| US9.1 (AC9.1.1) | 7 |
