# Functional Specification — u8-web-app

Upstream:
- `unit-of-work.md` (U8) and `unit-of-work-story-map.md`
- `stories.md`: US1.1–US4.2, US7.1, US7.2, US8.1, US8.2 and US9.1
- `requirements.md`: FR1.7, FR4, FR5, FR6, FR9, FR10, FR11, FR12, FR15 and NFR3, NFR4, NFR9
- `components.md` (DoctorWebApp)
- `contract-summary.md`: C8 and its R-02 additions, C7 and C9
- Refined mockups: `mockups.md`, `interaction-spec.md`, `design-system-mapping.md` and `accessibility-checklist.md`

Screen components are listed in `frontend-components.md`.

## Purpose

U8 is a single-page React app that talks only to the local U4 server (C8) and the knowledge API (C9). It owns no data. The U6 prescription and follow-up screens and the U7 benchmark screen are out of scope, because those units were cut by the person on Oct 30. The app shows only the features `/api/features` reports, so those screens never appear.

## Workflows

- **W1 Sign-in and first run** (screens 01, 02):
  1. List the profiles and sign in with `POST /api/session`.
  2. On first sign-in, show the disclaimer. "Accept and continue" stays disabled until both boxes are ticked. Accepting calls `POST /api/disclaimer`.
  3. The tour is cut (Could). The disclaimer screen goes straight to Patients.
- **W2 Patients** (screen 03):
  1. Search as the user types, with a 250 ms debounce. Show a status chip on each result.
  2. With no results, show "No patients found" and "Create new patient".
  3. Creating a patient opens the workspace. "Exit case" returns here.
- **W3 Workspace** (screens 04–13):
  - **Layout:** a sticky patient card, chat on the left and the map on the right.
  - **Walk stream:** the walk streams over SSE using `fetch` with a `ReadableStream`.
    - `form` events open chat forms: confirm findings, needs data, patient details or edit treatment.
    - Once submitted, a form shrinks to a one-line summary.
    - `line` events add chat lines with node chips, under fixed section headers.
    - `map_update` events light up nodes and edges in order.
    - `done` shows the summary: steps, cited, ungrounded, pack version and provider.
    - `error` shows a plain message with Retry, keeping all inputs. Retry sends `continue` with the same `walkId`.
  - **Banners:** a newer pack version shows the banner "Newer version vX.Y available: re-walk?". A read-only second tab shows a banner and disables input.
  - **Tab lock:** a heartbeat every 15 s, released on `beforeunload`. The `X-Brahma-Tab` header carries the ID stored in `sessionStorage`.
  - **Out of knowledge:** the ⊘ state with "Suggest adding this branch", which opens Knowledge.
  - **Explore and stop:** shown as a separate lane on the map and in the chat.
- **W4 Selection sync:** clicking a chat line selects its node and opens the panel. Clicking a node highlights its line. Both work from the keyboard with Enter and Space.
- **W5 Node panel** (screens 09, 11):
  - Shows the node detail (type, drug, route, dose and formula, frequency, review point, safety checks, sources, version and comments).
  - Safety results show "! Allergy conflict" with the node chip, or "? Not checked: no grounded safety data".
  - Edit opens an edit-treatment chat form, applied with `POST /api/cases/{id}/treatment-edits`. The edited field then shows "✎ edited".
- **W6 History** (screen 16):
  - List sessions with filters (outcome, text).
  - Open a session's detail with its why and audit entries.
  - Replay the session on the map, read-only, using the session's recorded version.
  - Export as JSON or PDF.
- **W7 Knowledge** (screen 17):
  - Pick a node, add a source URL, the change and a comment, and submit.
  - Show the before-and-after view with the source passage and any copy flag.
  - The reviewer profile sees Publish and Reject buttons. Publish is disabled when the copy flag is set (409).
  - Show the version history.
  - If submitting fails, keep the input and show the message.
- **W8 Shell:**
  - The header shows the profile, navigation, the "Decision support, not diagnosis" text and the pack chip(s) on every screen.
  - Below 1280 px, show the desktop-only notice.

## State Machines

The workspace screen moves between these states: empty, confirm findings, working, needs more data, answered, exploring, edit treatment, out of knowledge and error (FR5.6). The current state comes from the last walk event, or from the case view on reload.

## Rules

- **R1** The app never shows model text that didn't arrive as a `line` event, which means it has passed the check.
- **R2** A result is shown with a symbol and a word as well as a colour: ↓ Low, ↑ High, ! Abnormal, ✓ Normal, ? Not yet tested, ◷ Planned (FR5.7).
- **R3** All five NFR3 accessibility items from `accessibility-checklist.md` apply: keyboard use, contrast, labels, focus order and no information carried by colour alone.
- **R4** Patient names and IDs carry the label "synthetic" (FR15.2).

## Error Handling

Every API error uses the `{error: {code, message, retryable}}` shape. The message is shown as written, with Retry when the error is retryable. A 401 sends the user to sign-in.

## Acceptance Criteria Handled Elsewhere

- The data behind each screen comes from u2, u3, u4 and u5.
- US5.1 and US6.1 (U6) and the benchmark page (U7) are cut.
- AC1.2.3, the tour, is cut (Could).
