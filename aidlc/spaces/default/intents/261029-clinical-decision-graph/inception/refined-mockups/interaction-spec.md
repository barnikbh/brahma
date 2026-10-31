# Interaction Specification — Brahma

Upstream: `mockups.md` (annotations A1–A8), `wireframes.md`, `user-flow.md`, `stories.md`, `requirements.md`. Component format follows the framework's component-spec template, kept short for the hackathon (project rule: keep process detail light). Responsive behaviour is desktop-only for every component (see `mockups.md`, Responsive Behaviour), so per-component breakpoint tables are omitted.

## Interaction Model

- **Chat-first:** the doctor types; Brahma replies with text, a pathway, or a form. Forms are messages in the thread (Q2).
- **Map mirrors chat:** selecting a chat line selects its node, and selecting a node highlights its line (FR5.3).
- **Detail on demand:** node detail opens in a side panel over the right edge of the map; Escape or the close button returns focus to the line or node that opened it.
- **Dialogs:** only the Void reason (FR7.7) and sign-out confirmation. Everything else is inline.
- **Every map action posts to the chat** (FR5.8), so the thread is the case record.

## Components

### ChatForm

| Field | Value |
|---|---|
| Component | ChatForm |
| Description | A form Brahma posts into the chat when it needs structured input (Confirm findings, Needs more data, Edit treatment, Patient details) |
| Category | input |

| State | Description | Trigger |
|---|---|---|
| open | Dark 2 px outline, label "form · needs your input" | Brahma posts it |
| invalid | Offending chip marked "!" with words; submit disabled | Non-number, unconvertible unit, unresolved conflict (FR4.11) |
| submitting | Submit shows a spinner; inputs locked | Submit |
| submitted | Collapses to a one-line summary; the doctor's answer appears as their own message | Success |
| error | "Couldn't send. Your entries are kept." + Retry | Failure |
| read-only | Disabled | Case open in another tab (A5) |

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| kind | 'confirm-findings' \| 'needs-data' \| 'edit-treatment' \| 'patient-details' | yes | — | Which form |
| fields | object[] | yes | — | Prefilled fields or chips |
| onSubmit | function | yes | — | Sends the answer |

| Requirement | Implementation |
|---|---|
| ARIA role | `form` with `aria-labelledby` its heading |
| Keyboard | Tab through fields; Enter submits when valid; chips removable with Delete |
| Screen reader | Announces "Brahma needs your input: <form name>" when posted (polite live region) |
| Focus | Moves to the first field when posted; returns to the composer after submit |

### PathwayAnswer

| Field | Value |
|---|---|
| Component | PathwayAnswer |
| Description | The cited pathway: summary, counts, and eight ordered sections of lines, each with node chips (FR4.6) |
| Category | display |

| State | Description | Trigger |
|---|---|---|
| streaming | Sections fill in walk order; progress line above. Each line runs the claim check (FR4.10) on the server **before** it is sent to the screen, so a line only ever appears after it has passed and is never shown and then withdrawn. While a section's lines are being checked, the section shows its heading with a small "Checking against sources…" marker (with `aria-busy="true"`). A line that fails is never sent, and the held-back notice appears when the walk ends | Walk running (NFR1: first progress ≤ 3 s) |
| answered | Full pathway; counts; model and pack chips (A1) | Walk complete |
| held-back | "1 line held back: did not match its source" notice | Claim check rejects a line (FR4.10) |
| out-of-knowledge | "No grounded answer" with ⊘ and "Suggest adding this branch"; no diagnosis or treatment lines | No match (FR4.5) |
| selected-line | Line highlighted; its node selected on the map | Line or node clicked |

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| sections | object[] | yes | — | Ordered sections with lines and node IDs |
| counts | object | yes | — | steps, cited, ungrounded |
| packVersion | string | yes | — | e.g. "IBD v1.3" |
| model | string | yes | — | Provider and model name |

| Requirement | Implementation |
|---|---|
| ARIA role | `article` with `h3` per section |
| Keyboard | Each line is a button; Enter selects it and opens its node |
| Screen reader | Line reads its text, then "source N12" |
| Focus | Stays on the line; panel opens without stealing focus unless Enter is pressed again |

### NetworkMap

| Field | Value |
|---|---|
| Component | NetworkMap (React Flow) |
| Description | The graph region used, in fixed columns Findings → Diagnosis → Tests → Sub-type → Treatment → Monitor (FR5.2) |
| Category | display |

| State | Description | Trigger |
|---|---|---|
| empty | Columns with no nodes; hint "The map fills in as Brahma walks" | New case |
| walking | Nodes and edges light up in walk order | Walk running (FR5.4) |
| answered | Walked path solid indigo; bypassed grey; not taken dashed | Walk complete |
| exploring | Side lane in fuchsia dashed | Explore (FR4.7) |
| replay | Read-only; pinned version label | Replay from History (FR9.5) |

| Prop | Type | Required | Default | Description |
|---|---|---|---|---|
| nodes, edges | object[] | yes | — | With status (used, entry, test needed, not in pack) |
| selectedNodeId | string | no | — | Synced with the chat |
| zoom | number | no | 100 | 40–200 in 20 steps (FR5.5, Could) |

| Requirement | Implementation |
|---|---|
| ARIA role | `application` region labelled "Graph region used"; nodes are buttons |
| Keyboard | Arrow keys move between nodes in walk order; Enter opens detail; +/− zoom; 0 fits |
| Label | Each node `aria-label`: "<type>, <label>, <status>, <result>" (NFR3) |
| Contrast | Node text 4.5:1; edges 3:1 against the map background |

### NodeDetailPanel

| Field | Value |
|---|---|
| Component | NodeDetailPanel |
| Description | Side panel with a node's content, source, version, comments; for treatment tiers, the full plan and safety lines (FR6.1, A3) |
| Category | display |

| State | Description | Trigger |
|---|---|---|
| loading | Spinner | Opened |
| default | "Suggested by pack vX.Y" | Loaded |
| edited | "Edited by <profile>"; fields marked "✎ edited" | Edit applied (FR6.4) |
| error | "Couldn't load this node" + Retry | Failure |

| Requirement | Implementation |
|---|---|
| ARIA role | `complementary` with `h3` node title |
| Keyboard | Escape closes; actions (Edit treatment, Explore, Suggest a change) are buttons |
| Focus | Moves to the panel heading on open; returns to the origin on close |

### PatientCard

| Field | Value |
|---|---|
| Component | PatientCard |
| Description | Sticky card: name, age, sex, weight, case ID "synthetic", first comorbidity, allergy in red with ⚠ and the word "Allergy" |
| Category | display |

| State | Trigger |
|---|---|
| placeholder | New case: "Describe the patient in the chat; details fill in here" |
| collapsed (default) / expanded | Expand ▾ / Collapse ▴ (`aria-expanded`) |
| updated | Patient details saved; chat confirms the change (FR4.9) |

### Banners

| Banner | Text | Trigger | Style |
|---|---|---|---|
| Version (A2) | "This case used IBD v1.3. v1.4 is live." + Re-walk / Dismiss | Reopen after a publish (FR1.7) | Sage information |
| Read-only (A5) | "This case is open in another tab. This view is read-only." | Second tab (NFR7) | Sage information |
| Disclaimer | "Decision support, not diagnosis." + page-specific line | Always (FR15.1) | Sage note bar |
| Too narrow | "Brahma is built for desktop screens (1280 px and up)" | Width < 1280 px | Sage information |

### ResultChip

| Result | Symbol + word | Colour (text on tint) |
|---|---|---|
| Below range | ↓ Low | Red #B91C1C |
| Above range | ↑ High | Red #B91C1C |
| Abnormal | ! Abnormal | Red #B91C1C |
| Normal | ✓ Normal | Green #15803D |
| Not yet tested | ? Not yet tested | Amber #B45309, dashed |
| Planned | ◷ Planned | Grey #525252 |
| Not checked (safety) | ? Not checked | Amber #B45309 |

Colour is never the only cue (NFR3).

## Key Interaction Flows

1. **Demo walk (US3.1 → US3.2 → US3.3):** type case → ChatForm confirm-findings → submit → PathwayAnswer streaming + NetworkMap walking → ChatForm needs-data → submit → answered.
2. **Verify a step (US4.1):** click a line or a node → NodeDetailPanel → read source → Escape back.
3. **Edit (US4.2):** panel "Edit treatment" or chat "change dose to 40 mg" → ChatForm edit-treatment → apply → panel shows "Edited by".
4. **Suggest and publish (US8.1 → US8.2):** panel "Suggest a change" → Knowledge screen form → proposal → switch to the reviewer profile → reviewer view (A6) → Publish.
