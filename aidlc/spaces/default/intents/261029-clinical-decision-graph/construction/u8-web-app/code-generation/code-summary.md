# Code Summary — u8-web-app

## Built

The doctor web app lives in `web/` (Vite, React, TypeScript strict mode, Tailwind, shadcn/ui and React Flow). It includes:

- Sign-in, the disclaimer, and patient search, create and reopen.
- The workspace:
  - a sticky patient card
  - chat with checked lines and node chips
  - the confirm-findings, needs-data, patient-details and edit-treatment forms
  - a walk summary
  - the live map, which lights up as the walk runs, stays in sync with the chat, and has an explore lane
  - banners for a newer pack version and for read-only cases
  - error and retry, and out of knowledge
- The node panel, showing dose with its formula and the safety lines.
- History, with filters, the "why", replay and export.
- Knowledge: propose, before and after, the copy flag, and reviewer publish and reject.
- The disclaimer and pack chips on every screen.

U4's server serves `web/dist` at `/`, so `python -m brahma.server` runs the whole app at `http://127.0.0.1:8000`.

## Files

- **Created:**
  - `web/`: config, `src/` (api, state, components, pages, tests) and `e2e/demo.spec.ts`
  - `tests/server/test_web_app.py`
- **Modified:**
  - `src/brahma/server/app.py` (`mount_web_app`, which serves the app with an SPA fallback, never shadows `/api` and blocks path traversal)
  - `src/brahma/server/config.py` (`web_dist`, `recorded_dir`)
  - `src/brahma/server/services.py`
  - `.env.example` (adds `BRAHMA_RECORDED_DIR`)
  - `README.md` (Run the app)
  - `.github/workflows/ci.yml` (web job)
  - `.gitignore` (`web/node_modules`, `dist`, `coverage`, `test-results`, `playwright-report`)

## Tests (from the build run)

- **Web:** lint, typecheck, Prettier and build pass. `npm run test -- --coverage` gives 69 tests and 92.89% line coverage.
- **Python:** 340 tests pass with 96.99% coverage. Ruff and mypy are clean.
- **`npm run e2e`:** 1 test passes. It covers the full demo walk, 0 ungrounded lines, opening the node panel, and the session appearing in History.
- **Manual browser walk:** the demo answers with 24 steps, 27 cited and 0 ungrounded.

## Deviations

1. The new `BRAHMA_RECORDED_DIR` setting points the recorded provider at the demo fixtures. Use it for rehearsals and the end-to-end test.
2. Extra dev packages: `@testing-library/dom` and `@types/node`.
3. The "✎ edited" marker is kept only in the browser. Node detail always returns `edited: null`, so the marker disappears after a reload.
4. Not built: form drafts and a zoom slider. React Flow's own +/−/fit controls are there.

## Demo Risks

- **Shared database connection:** U4 shares one SQLite connection across threads with no lock. Overlapping requests can raise a 500 error. The web app works around it by not starting the lock heartbeat until the case has loaded, and by skipping it while another request is running. The real fix is a database lock in U4.
- **Small nodes in the full map:** the full IBD map makes nodes small. Zoom in while recording the video.
