# Frontend Components — u8-web-app

Upstream: `functional-spec.md` (U8), `mockups.md`, `interaction-spec.md`, `design-system-mapping.md` and `contract-summary.md` (C8, C9).

| Component | Screen | Responsibility |
|---|---|---|
| `AppShell` | all | Header with profile, nav, disclaimer and pack chip(s); desktop-only notice; routes |
| `SignInPage` | 01 | Profile cards; sign in |
| `DisclaimerPage` | 02 | Two checkboxes; Accept disabled until both are ticked |
| `PatientsPage` | 03 | Search, status chips, empty state, "Create new patient" |
| `WorkspacePage` | 04–13 | Owns the case view, walk stream state machine, lock heartbeat and banners |
| `PatientCard` | workspace | Sticky card; patient details form trigger |
| `ChatThread` / `ChatLine` / `NodeChip` | workspace | Messages, section headers, cited lines with chips, collapsed submitted forms |
| `ChatForm` (`ConfirmFindings`, `NeedsData`, `PatientDetails`, `EditTreatment`) | 05, 07, 11 | Forms from `form` events; inline validation states (A4) |
| `WalkSummary` | 08 | Steps, cited, ungrounded, pack version, provider |
| `GraphCanvas` | workspace, history | React Flow with fixed columns (Findings → Diagnosis → Tests → Sub-type → Treatment → Monitor), node badges, edge styles, explore lane |
| `NodePanel` | 09 | Node detail, dose formula, safety (A3), sources, comments, edit |
| `HistoryPage` / `SessionDetail` | 16 | Filters, list, detail, read-only replay, export |
| `KnowledgePage` / `ProposalView` | 17 | Proposal form, before-and-after view, copy flag, reviewer actions, version history |
| `api/client.ts` | — | Typed fetch wrapper, error shape, tab header, 401 redirect |
| `api/walkStream.ts` | — | SSE parser over `fetch` |

The stack is Vite, React and TypeScript in strict mode, with Tailwind, shadcn/ui and React Flow (`@xyflow/react`). Tokens come from `design-system-mapping.md`.
