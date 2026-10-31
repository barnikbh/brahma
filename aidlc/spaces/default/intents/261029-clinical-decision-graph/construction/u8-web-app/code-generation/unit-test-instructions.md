# Unit Test Instructions — u8-web-app

## Framework and Setup

- Vitest with jsdom and React Testing Library. Configuration is in `web/vite.config.ts`.
- Requires Node 20+. Install once with `npm install`, run from `web/`.
- No server or network is needed. `web/src/test/fakeApi.ts` mocks `fetch` with C8 and C9 fixtures, including a fake SSE stream of the demo walk.

## Run This Unit's Tests

Run each command from `web/`.

```bash
npm run test
```

With coverage (fails if line coverage drops below 80%):

```bash
npm run test -- --coverage
```

Lint and type checks:

```bash
npm run lint
```

```bash
npm run typecheck
```

Local smoke test. It starts `python -m brahma.server` with the recorded provider through Playwright's `webServer`:

```bash
npm run e2e
```

## Expected Coverage

- **Unit target:** at least 80% line coverage on `web/src`. This is the frontend floor from the Testing Contract, and CI checks it.
- **Backend:** the single server change is covered by `tests/server/` under the existing Python floor.

## Tests Per Component

| Component | File | About |
|---|---|---|
| API layer | `web/src/api/*.test.ts` | 6 |
| Walk reducer and hooks | `web/src/state/*.test.ts` | 10 |
| Shell, sign-in, patients | `web/src/pages/{SignIn,Disclaimer,Patients}.test.tsx`, `AppShell.test.tsx` | 6 |
| Workspace | `web/src/pages/Workspace.test.tsx`, `components/GraphCanvas.test.tsx` | 10 |
| Node panel | `web/src/components/NodePanel.test.tsx` | 3 |
| History and Knowledge | `web/src/pages/{History,Knowledge}.test.tsx` | 6 |
| Smoke (local) | `web/e2e/demo.spec.ts` | 1 |

## Mocking and Test Data

- All fixtures are synthetic and mirror the U4 recorded demo walk.
- React Flow is tested through its rendered DOM. Tests use `ResizeObserver` and `DOMMatrix` stubs in the setup file.
