# Refined Mockups — Brahma

**High-fidelity source:** your Brahma design handover. Screens are in `docs/design-handover/wireframes/screens/` (PNG, 1440 px), the clickable version is in `docs/design-handover/wireframes/html/`, and the spec is `docs/design-handover/Brahma - Design Handover.md`. These are the refined mockups; this document maps every story to its screen and adds the annotations the approved requirements need since the handover was drawn (Q1).

**Upstream:** `wireframes.md` and `user-flow.md` (rough mockups, fixes R-01, R-02), `stories.md` (US1.1–US9.1), `requirements.md` (FR, NFR), `team-practices.md` (desktop, local). Answers: `refined-mockups-questions.md` Q1–Q6.

## Story-to-Screen Map

| Story | Priority | Screen(s) (handover PNG) | Wireframe |
|-------|----------|--------------------------|-----------|
| US1.1 Pick a demo profile | Must | 01 Sign-in | S1 |
| US1.2 Disclaimer and tour | Must (tour Could) | 02, 02b First sign-in | S1a |
| US2.1 Find, create, reopen | Must | 03 Patients, 04 Workspace new patient | S2 |
| US3.1 Describe and confirm | Must | 05 Confirm findings | S3 (3a) |
| US3.2 Grounded pathway | Must | 06 Working, 08 Answered | S3 (3b, 3d) |
| US3.3 Needs more data | Must | 07 Needs more data | S3 (3c) |
| US3.4 No grounded answer, error | Must | 12 Out of knowledge, 13 Error | S3 (3f, 3g) |
| US3.5 Map | Must (zoom Could) | 06, 08; Graph option E | S3 |
| US3.6 Explore | Should | 10 Exploring a side pathway | S3 (3h) |
| US4.1 Treatment detail | Must | 09 Treatment detail panel | S4 |
| US4.2 Edit treatment | Should | 11 Edit treatment via chat form | S4 (3i) |
| US5.1 Prescription | Could | 14, 14b Prescription | S5 |
| US6.1 Follow-up | Could | 15, 15b Follow-up visit | S6 |
| US7.1 Audit and why | Must | 16 Session history | S7 |
| US7.2 History, replay, export | Must (export Could) | 16 Session history | S7 |
| US8.1 Suggest a change | Must | 17 Knowledge update | S8 |
| US8.2 Review and publish | Must | 17 Knowledge update (reviewer view, annotated below) | S8 |
| US8.3 Background check | Could | No screen (results appear as proposals in 17) | S8 |
| US9.1 Urology walk | Should | 01 (urologist profile), 03 (P-1024), 08 layout on the urology pack | S2, S3 |

## Annotations Since the Handover

These change or add to the handover screens. Each is drawn as a small text or chip in the existing layout; no new screen is needed.

### A1 — Claim check and ungrounded count (screen 08; FR4.10, US3.2)

```text
+--------------------------------------------------+
| Pathway  [IBD v1.3]  [Model: Meta <name>]        |
| SUMMARY: UC pancolitis (E3), severe -> Tier 2    |
| [18 steps] [18 cited] [0 ungrounded]             |
|                                                  |
| (if a line failed the claim check:)              |
| [1 line held back: did not match its source]     |
|   > View in audit                                |
+--------------------------------------------------+
```

- The held-back notice is shown only when the count is above 0; the line itself never appears.
- The model chip is new (FR14.3).

### A2 — Version banner on a reopened case (screens 04 and 08; FR1.7, US2.1)

```text
+----------------------------------------------------------------------+
| This case used IBD v1.3. v1.4 is live.   [Re-walk on v1.4] [Dismiss] |
+----------------------------------------------------------------------+
```

- Sits under the patient card, above both panels. Information style (sage), not a warning colour.

### A3 — Safety "Not checked" (screens 09 and 14; FR1.6, FR7.3, US4.1, US5.1)

```text
+------------------------------------------+
| Safety                                   |
| !  Allergy conflict: penicillin class    |
|    [N21]                                 |
| ?  Interactions: Not checked             |
|    no grounded safety data               |
| OK Pregnancy: no contraindication [N22]  |
+------------------------------------------+
```

- Every line has a symbol and words. "Not checked" never reads as a pass.

### A4 — Input checks in Confirm findings (screen 05; FR4.11, US3.1)

```text
+------------------------------------------------+
| form: needs your input                         |
| [Metric  Hb  10.2 g/dL  (entered 102 g/L)]     |
| [Metric  Calprotectin  abc ug/g] ! Not a number|
| Two Hb values: ( ) 10.2 g/dL  ( ) 9.1 g/dL     |
| [Looks right - walk the graph]  (disabled)     |
+------------------------------------------------+
```

- The walk button stays disabled until invalid chips are fixed and conflicts are chosen.

### A5 — Read-only second tab (any case screen; NFR7)

```text
+---------------------------------------------------------------+
| This case is open in another tab. This view is read-only.     |
+---------------------------------------------------------------+
```

- Composer, forms and edit buttons are disabled; history and the map stay viewable.

### A6 — Reviewer view of a proposal (screen 17; FR10.4, FR10.9, US8.2)

```text
+--------------------------------------------------------------+
| Proposed version v1.3 -> v1.4   by Dr. Maya   [Proposed]     |
| BEFORE v1.3            | AFTER v1.4 draft                    |
| ...                    | ...                                 |
| Source passage: "<passage the change came from>"             |
| ! Possible verbatim copy (32 words)   - publish blocked      |
| Reviewer comment [                         ]                 |
| [Publish v1.4]  [Reject]                                     |
+--------------------------------------------------------------+
```

- Shown only to the demo clinical reviewer profile. Dr. Maya sees the same panel without Publish and Reject.

### A7 — No verdict without a response criterion (screen 15b; FR8.4, US6.1)

- Each measure with no criterion node shows its trend with "⊘ No grounded response criterion for this measure" and "Suggest adding it", in place of a verdict tag.

### A8 — Benchmark page: grounded share and agreement (screen 18; FR13.5, FR13.6, FR13.9)

- The summary cards gain a second pair: "Agreement with expected pathway: graph X% / plain Y%". The filter splits IBD into "IBD: UC" and "IBD: Crohn's", plus "Urology stub (not counted)".
- The pass card states both parts: "≥ 95% grounded" and "beats plain model on both".

## States Per Screen

| Screen | Loading | Empty | Error | Success | Screen-specific |
|--------|---------|-------|-------|---------|-----------------|
| Sign-in | — | — | Profiles failed to load: message + Retry | Lands on Patients or first-run | — |
| First run | — | — | Acceptance failed to save: message + Retry | Patients | Accept disabled until both ticked |
| Patients | Skeleton rows | "No patients found" + Create | Search failed: message + Retry | List | — |
| Workspace | Progress lines in chat; map lights up | 2 Empty (new case) | 3g Error + Retry, inputs kept | 3d Answered | 3a, 3c, 3e, 3f, 3h, 3i; A2 banner; A5 read-only |
| Node panel | Spinner in panel | — | "Couldn't load this node" + Retry | Detail | Edited by; A3 safety |
| Prescription | Draft building | No plan yet: "Answer the case first" | PDF failed: message + Retry; not marked complete | Signed + Download | Blocked sign; VOID |
| Follow-up | Charts loading | First visit: no earlier points | Results failed to save + Retry | Verdict | A7 no criterion |
| History | Skeleton rows | "No sessions yet" | Load failed + Retry | Detail | Replay read-only; export |
| Knowledge | — | No versions beyond v1.0 | Submit failed, input kept | Proposal created | A6 reviewer; copy flag; fetch refused |
| Benchmark | Run in progress: n of 20 | "No benchmark run yet" | Run stopped: Resume | Results | A8 |

## Responsive Behaviour

Desktop and laptop only (Q6; NFR4). Designed at 1440 px and works down to 1280 px:

| Width | Behaviour |
|-------|-----------|
| ≥ 1440 px | As drawn: chat ~40%, map ~60% |
| 1280–1439 px | Chat keeps a 440 px minimum; the map panel narrows and scrolls horizontally inside its frame |
| < 1280 px | Not supported. A notice reads "Brahma is built for desktop screens (1280 px and up)" |

## Assumptions & Open Questions

- [assumption] The handover PNGs stay the visual source of truth; where an annotation here differs from a PNG, this document wins because it reflects the approved requirements.
- Open: the reviewer view (A6) is new and was not drawn in the handover; add it to your design canvas if you want it in the video.
