# Logical Components — u8-web-app

Upstream: `performance-requirements.md`, `security-requirements.md` and `tech-stack-decisions.md` (U8), `functional-spec.md` and `frontend-components.md` (U8), `contract-summary.md` (C8, C9).

| Folder | Contents |
|---|---|
| `web/src/api/` | `client.ts` (typed fetch, error format, tab header, 401 redirect), `walkStream.ts` (SSE parser), `types.ts` (C8 and C9 types) |
| `web/src/state/` | `walkReducer.ts` (workspace state machine), `useCase.ts`, `useLock.ts` (15 s heartbeat, release on page unload) |
| `web/src/components/` | AppShell, PatientCard, ChatThread, ChatLine, NodeChip, ChatForm and its variants, WalkSummary, GraphCanvas, NodePanel, ResultBadge, Synthetic, banners, plus the shadcn/ui primitives in `ui/` |
| `web/src/pages/` | SignIn, Disclaimer, Patients, Workspace, History, Knowledge |
| `web/e2e/` | Playwright smoke test of the demo walk |

Each layer imports only from the layers below it: pages use components and state, components use state and api, and state uses api.
