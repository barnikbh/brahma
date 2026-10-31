# CI/CD Pipeline — u8-web-app

Upstream: `logical-components.md` and `security-design.md` (U8 NFR design), `functional-spec.md` (U8 workflows W1–W8), `components.md` (DoctorWebApp), `contract-summary.md` (C8, C9).

There is no deployment. Delivery is a green CI run on `main`.

## Pipeline Additions

A new `web` job in `.github/workflows/ci.yml` runs on Node 20, in the `web/` working directory.

| # | Step | Command | Gate | NFR |
|---|---|---|---|---|
| 1 | Install | `npm ci` | Fails on error | NFR10 |
| 2 | Lint and types | `npm run lint && npm run typecheck && npx prettier --check .` | Any error fails | NFR12, NFR8.6 |
| 3 | Unit tests | `npm run test -- --coverage`, with an 80% line threshold in the Vitest config | Below 80%, or any failure, fails | NFR9, NFR2.2, NFR3.1 |
| 4 | Build | `npm run build` | Fails on error | NFR4.4 |

The Playwright smoke test (`npm run e2e`) runs locally against `python -m brahma.server` with the recorded provider. It is not part of CI.
