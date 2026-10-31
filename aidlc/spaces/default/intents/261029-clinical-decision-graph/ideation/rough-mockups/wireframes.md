# Wireframes — Brahma (Clinical Decision Graph)

Low-fidelity wireframes for the first version, following your design handover. Visual detail, colour tokens and full-resolution screens live in the source; this file pins down structure, states, accessibility and scope.

**Source of truth for visuals:** `docs/design-handover/Brahma - Design Handover.md` and `docs/design-handover/wireframes/` (PNG screens 01–18, clickable HTML, PDF).

**Upstream:** `intent-statement.md` (problem, primary user, decision support not diagnosis), `scope-document.md` (in/out of scope, milestones, Crohn's at full depth), `intent-backlog.md` (IB-01 … IB-13). Answers: `rough-mockups-questions.md` Q1–Q8.

## Design decisions (from your wireframes and answers)

| Decision | Choice | Source |
|----------|--------|--------|
| Main layout | Split view: chat left, network map right, sticky patient card above both | Q2; screens 04–13 |
| Answer format | Summary line (sub-type, entry tier, steps / cited / ungrounded counts) above the structured pathway; every line has a node chip | Q3; screen 08 |
| Patient input | Free text in chat, read back as an editable "Confirm findings" form before the walk; all structured input arrives as forms inside the chat | Q4; screen 05 |
| Screens in v1 | Sign-in, first-run, Patients, Workspace (all states), node detail, prescription, follow-up, history, knowledge, benchmark | Q5, Q8 |
| Devices | Desktop and laptop (1440 px design width); tablet out | Q6 |
| Graph view | Network map (option E): fixed columns Findings → Diagnosis → Tests → Sub-type → Treatment → Monitor/watch | Handover, Graph view |
| Crohn's disease | Authored at full depth; ⊘ on Crohn's in the wireframes is an example of the out-of-knowledge state only | Q7; scope-document.md |
| Added screens | Explore, edit treatment, prescription, follow-up and tour all built for Nov 2 | Q8 |

## Information architecture

```text
Sign-in
  +-- First sign-in: disclaimer -> tour (3 steps, skippable)
  +-- Patients (landing)
        +-- Workspace (one case)  [enter from Patients, leave with Exit case]
        |     +-- states: empty, confirm, working, needs data, answered,
        |     |           exploring, edit treatment, out of knowledge, error
        |     +-- Node detail panel (from map or chat line)
        |     +-- Generate prescription -> signed PDF
        |     +-- Follow-up visit (results, trends, assessment)
        +-- History (session list -> session audit detail)
        +-- Knowledge (suggest a change, proposed version, version history)
        +-- Benchmark (20 synthetic cases, graph vs plain model)
```

Global on every screen: top nav, knowledge pack and version chip, signed-in doctor, and the sage disclaimer bar "Decision support, not diagnosis".

## Screens

### S1 — Sign-in (screen 01)

```text
+------------------------------------------------------------------------------------------+
| [B] Brahma  -  Clinical decision graph                                                   |
|                                                                                          |
|           Sign in (h1)                                                                   |
|           For registered medical practitioners only                                      |
|                                                                                          |
|           Choose a demo account:                                                         |
|           ( ) Dr. Maya - gastroenterologist                                              |
|           ( ) Demo urologist                                                             |
|                                                                                          |
|           [ Sign in ]                                                                    |
|                                                                                          |
+------------------------------------------------------------------------------------------+
| Decision support, not diagnosis. Synthetic patients only.                                |
+------------------------------------------------------------------------------------------+
```

- Demo build only: seeded accounts, no open sign-up (scope-document.md, Out of Scope).
- **Accessibility:** h1 "Sign in"; landmarks header, main, footer (disclaimer); keyboard entry point is the first account radio.

### S1a — First sign-in: disclaimer and tour (screens 02, 02b)

```text
+------------------------------------------------------------------------------------------+
| [B] Brahma   Patients | History | Knowledge | Benchmark   [IBD v1.3] Dr.Maya             |
+------------------------------------------------------------------------------------------+
| Decision support, not diagnosis. Synthetic patients only.                                |
+------------------------------------------------------------------------------------------+
| Step 1 of 4: Before you start (h1)                                                       |
|                                                                                          |
| Decision support, not diagnosis. You stay responsible for every decision,                |
| prescription and order.                                                                  |
|                                                                                          |
| [ ] I am responsible for every clinical decision I make with Brahma                      |
| [ ] I will use synthetic patients only (demo)                                            |
|                                                                                          |
| [ Accept and continue ]  (disabled until both ticked; logged once)                       |
+------------------------------------------------------------------------------------------+
| Steps 2-4 tour: Talk to Brahma | Read the map (legend) | Check, edit, sign               |
| [ Skip the tour ]                                        [ Next > ]                      |
+------------------------------------------------------------------------------------------+
```

- Acceptance is logged once with date and knowledge version; re-accept when the disclaimer or pack changes materially.
- **Accessibility:** h1 per step ("Before you start", "Talk to Brahma", "Read the map", "Check, edit, sign"); landmarks header, main; keyboard entry point is the first checkbox (step 1) or "Next" (steps 2–4).

### S2 — Patients (screen 03)

```text
+------------------------------------------------------------------------------------------+
| [B] Brahma   Patients | History | Knowledge | Benchmark   [IBD v1.3] Dr.Maya             |
+------------------------------------------------------------------------------------------+
| Decision support, not diagnosis. Synthetic patients only.                                |
+------------------------------------------------------------------------------------------+
| Good morning, Dr. Maya (h1)                                                              |
| +------------------------------------------+ +-----------------------------------------+ |
| | Find a patient (h2)                      | | New patient (h2)                        | |
| | [ search: case ID, finding, dx  ]        | | Opens a fresh case with a               | |
| |                                          | | generated ID tied to you.               | |
| | P-1042 Lakshmi R. UC pancolitis          | |                                         | |
| |   [Follow-up due today]   >              | | [ + Create new patient ]                | |
| | P-1039 diarrhoea 8wk calpro 420          | |                                         | |
| |   [? Needs data]          >              | | Next ID: P-1044                         | |
| | P-1031 headache 3wk                      | |                                         | |
| |   [Out of knowledge]      >              | |                                         | |
| | P-1024 urinary freq (urology)            | |                                         | |
| |   [Plan in place]         >              | |                                         | |
| +------------------------------------------+ +-----------------------------------------+ |
+------------------------------------------------------------------------------------------+
```

- Status chips pair symbol and word (Follow-up due, ? Needs data, ⊘ Out of knowledge, ✓ Plan in place). In the diagram these show as words only.
- **Accessibility:** h1 greeting, h2 per card; landmarks header, nav, main; keyboard entry point is the patient search field.

### S3 — Consultation workspace (screens 04–13)

The answered state (3d) is shown. Every other state is the same component started differently.

```text
+------------------------------------------------------------------------------------------+
| [B] Brahma   Patients | History | Knowledge | Benchmark   [IBD v1.3] Dr.Maya             |
+------------------------------------------------------------------------------------------+
| Decision support, not diagnosis. Synthetic patients only.                                |
+------------------------------------------------------------------------------------------+
| Lakshmi R. 34y F 58kg P-1042 (synthetic) [Hypothyroid +1] [ALLERGY Penicillin]           |
|                                        [Edit details] [Expand v] [Exit case]             |
+------------------------------------------------------------------------------------------+
| +------------------------------------------+ +-----------------------------------------+ |
| | Consultation chat (h2)                   | | Graph region used (h2)                  | |
| |                                          | | Legend: walked | bypassed |             | |
| | Brahma: Tell me about the patient        | | not taken | exploring                   | |
| | Dr: 34y woman, bloody stool 6mo,         | | [-] 100% [+] [Fit] [100%]               | |
| |     Hb 10.2, calpro 850                  | |                                         | |
| |                                          | | FINDINGS  DX   TESTS  SUBTYPE TREAT     | |
| | Brahma - pathway [IBD v1.3]              | | N1 ----+       N5                       | |
| | SUMMARY: UC pancolitis (E3),             | | N2 ----+- N4 -+N6 -- N9 ---- T1         | |
| | severe -> enters Tier 2                  | | N3 ----+       N7     N10 -> >T2        | |
| | [18 steps][18 cited][0 ungrounded]       | |           (inf N8           T3          | |
| | [Rx Generate] [Plan follow-up]           | |           colit)  (Crohn)               | |
| |                                          | |                                         | |
| | 1 FINDINGS            [N1-N3]            | | MONITOR/WATCH: N14 N15 N16 N17          | |
| | 2 WORKING DIAGNOSIS   [N4]               | | N18 (surgery trigger)                   | |
| | 3 CONFIRM AND REFINE  [N5-N8]            | |                                         | |
| | 4 REFINED SUB-TYPE    [N9-N10]           | | Selecting a chat line selects           | |
| | 5 TREATMENT TIERS     [N11-N13]          | | its node; selecting a node              | |
| | 6 MONITOR             [N14-N15]          | | highlights the line.                    | |
| | 7 DIET                [N16]              | |                                         | |
| | 8 WATCH-OUTS, SURGERY [N17-N18]          | |                                         | |
| |                                          | |                                         | |
| | [ Message the agent...  ] [Send]         | |                                         | |
| | hint: explore..., change dose...         | |                                         | |
| +------------------------------------------+ +-----------------------------------------+ |
+------------------------------------------------------------------------------------------+
```

| State | Artboard / screen | What changes from the diagram |
|-------|-------------------|-------------------------------|
| 2 Empty (new case) | 04 | Dashed patient-card placeholder; greeting only; map empty |
| 3a Confirm findings | 05 | Chat form of editable chips (kind, name, value, unit); "Looks right — walk the graph" |
| 3b Working | 06 | Progress lines in chat; nodes and edges light up in walk order |
| 3c Needs more data | 07 | Tests marked ? on the map; results form in chat (stool culture, colonoscopy + biopsy, extent, severity) |
| 3d Answered | 08 | As drawn |
| 3e Treatment detail | 09 | Node panel opens over the map (see S4) |
| 3f Out of knowledge | 12 | "No grounded answer"; ⊘ node; nothing guessed; "Suggest adding this branch" |
| 3g Error | 13 | Plain message and Retry; inputs kept |
| 3h Exploring | 10 | Side branch in a fuchsia dashed lane; "Add these tests to the plan" / "Stop exploring"; main plan unchanged |
| 3i Edit treatment | 11 | Edit form in chat prefilled from the suggestion; card expanded (see S4) |

- The answer pathway follows your value story: findings → working diagnosis → confirm and refine → sub-type → tiered treatment → monitor → diet → watch-outs and surgery triggers (intent-statement.md).
- Selection sync both ways: chat line ↔ map node.
- Every map action (explore, edit) also posts a line into the chat, so the thread is the case record.
- **Accessibility:** h1 case ID + "Consultation" (visually the card), h2 "Consultation chat" and "Graph region used"; landmarks header, nav, main with two labelled regions, complementary for the patient card; keyboard entry point is the chat composer; map nodes carry `aria-label` with type, status and result; zoom controls are buttons.

### S4 — Node detail and edit treatment (screens 09, 11)

```text
+------------------------------------------------------------------------------------------+
| [B] Brahma   Patients | History | Knowledge | Benchmark   [IBD v1.3] Dr.Maya             |
+------------------------------------------------------------------------------------------+
| Decision support, not diagnosis. Synthetic patients only.                                |
+------------------------------------------------------------------------------------------+
| Lakshmi R. 34y F 58kg P-1042 (synthetic) [Hypothyroid +1] [ALLERGY Penicillin]           |
|                                        [Edit details] [Expand v] [Exit case]             |
+------------------------------------------------------------------------------------------+
| +------------------------------------------+ +-----------------------------------------+ |
| | Chat (as in 3d)                          | | Node N12 - Tier 2 (h3)                  | |
| |                                          | | Suggested by pack v1.3                  | |
| | Brahma - form: needs your input          | | Type: Corticosteroid                    | |
| | Edit treatment (Tier 2)                  | | Drug: Methylprednisolone                | |
| | Drug  [Methylprednisolone v]             | | Route IV | Dose [60 mg]                 | |
| | Route [IV]  Dose [60 mg]                 | | Frequency [Once daily]                  | |
| | Freq  [Once daily]                       | | Review [day 3]                          | |
| | Duration [Review at day 3]               | | Pre-start: infection excluded           | |
| | [ Apply edit ]  [ Cancel ]               | | Safety: OK - no conflict with           | |
| |                                          | |   Penicillin allergy                    | |
| |                                          | | Source: [UC guideline, yr] p.[n]        | |
| |                                          | | Version v1.3 | 2 comments               | |
| |                                          | | [Edit treatment] [Explore]              | |
| |                                          | | [Suggest a change]                      | |
| +------------------------------------------+ +-----------------------------------------+ |
+------------------------------------------------------------------------------------------+
```

- Panel header changes to "Edited by Dr. Maya" after an edit; edited fields marked "✎ edited"; original suggestion, edit and editor logged to the session audit.
- mg/kg doses compute from the card's weight. Allergy and weight checks re-run on apply.
- Values in [brackets] are placeholders; the build takes every dose, frequency and duration from the cited source.
- **Accessibility:** h3 node title inside the panel; landmark complementary (panel), form inside the chat log; keyboard entry point is the panel's first action or the form's first field; focus returns to the originating node or line on close.

### S5 — Generate prescription (screens 14, 14b)

```text
+------------------------------------------------------------------------------------------+
| [B] Brahma   Patients | History | Knowledge | Benchmark   [IBD v1.3] Dr.Maya             |
+------------------------------------------------------------------------------------------+
| Decision support, not diagnosis. Synthetic patients only.                                |
+------------------------------------------------------------------------------------------+
| Lakshmi R. 34y F 58kg P-1042 (synthetic) [Hypothyroid +1] [ALLERGY Penicillin]           |
|                                        [Edit details] [Expand v] [Exit case]             |
+------------------------------------------------------------------------------------------+
| +------------------------------------------+ +-----------------------------------------+ |
| | Prescription editor (h2)                 | | Preview (h2)                            | |
| | [x] METHYLPREDNISOLONE  [N12]            | | Dr. Maya, MD, Reg [no.]                 | |
| |     IV | [60 mg] | [daily] | [3d]        | | Lakshmi R. 34y F 58kg P-1042            | |
| | [x] LEVOTHYROXINE       [Card]           | | ALLERGY: Penicillin                     | |
| |     existing medication                  | | Dx: UC pancolitis K51.0                 | |
| | [ + Add medicine ]                       | | Rx 1. METHYLPREDNISOLONE ...            | |
| |                                          | | Investigations, advice,                 | |
| | Safety checks                            | | warning signs, follow-up                | |
| | OK  Allergy cross-reaction               | | Footer: IBD v1.3 | audit S-0143         | |
| | OK  Pregnancy                            | | DEMO - SYNTHETIC PATIENT                | |
| | ?   Interactions (review)                | |                                         | |
| | !   Doses from source (placeholder)      | |                                         | |
| |                                          | |                                         | |
| | [ ] I take responsibility                | |                                         | |
| | [ Sign and generate PDF ]                | |                                         | |
| +------------------------------------------+ +-----------------------------------------+ |
+------------------------------------------------------------------------------------------+
```

- **What blocks signing (R-01):**

  | Check | Result | Effect on "Sign and generate PDF" |
  |-------|--------|-----------------------------------|
  | Allergy cross-reaction | ! conflict | Blocks: the line must be removed or changed |
  | Pregnancy | ! contraindicated | Blocks |
  | Doses from source | ! any [placeholder] dose, frequency or duration left | Blocks: a line can only be signed with a value taken from its cited node |
  | Interactions | ? flagged | Warns: signing needs a ticked "I have reviewed the flagged interactions" line, recorded in the audit |
  | Duplicate class | ? flagged | Warns, same acknowledgement |
  | Manual line ("not from the pack") | — | Allowed; printed with "Manual" and logged as outside the knowledge pack |

- **Where each prescription field comes from (R-01):** doctor name, qualifications, registration number and clinic come from the seeded demo doctor profile and are marked "demo" in the demo build; patient details come from the patient card (synthetic); diagnosis and its ICD-10 code come from the sub-type node and its source; drug, route, dose, frequency and duration come from the treatment node (or the doctor's logged edit); advice, warning signs and follow-up dates come from the monitor, diet and watch-out nodes. Every demo PDF carries the "DEMO - SYNTHETIC PATIENT" watermark.
- **Sign:** requires the responsibility checkbox; stamps the time, the prescription ID and the knowledge version, saves the PDF to the case audit, and offers Download PDF and Print.
- **Void and re-issue (R-01):** asks for a reason, marks the signed prescription "VOID" in the audit and on its PDF (never deleted), and opens a new draft prefilled from it, which goes through the same checks and signing.
- **Accessibility:** h2 "Prescription editor" and "Preview"; landmarks header, main with two regions; keyboard entry point is the first medicine's include toggle; check results use symbol + word.

### S6 — Follow-up visit and trends (screens 15, 15b)

```text
+------------------------------------------------------------------------------------------+
| [B] Brahma   Patients | History | Knowledge | Benchmark   [IBD v1.3] Dr.Maya             |
+------------------------------------------------------------------------------------------+
| Decision support, not diagnosis. Synthetic patients only.                                |
+------------------------------------------------------------------------------------------+
| Lakshmi R. 34y F 58kg P-1042 (synthetic) [Hypothyroid +1] [ALLERGY Penicillin]           |
|                                        [Edit details] [Expand v] [Exit case]             |
| [Tier 2 IV steroids] [Visit 3 - day 14 - 12 Nov 2026]                                    |
+------------------------------------------------------------------------------------------+
| +------------------------------------------+ +-----------------------------------------+ |
| | Follow-up chat (h2)                      | | Timeline (h2)                           | |
| | Brahma: response measures are            | | dx -> day 3 -> visit 2 -> today         | |
| | Hb [N15], calpro [N14], stool            | |                                         | |
| | frequency, bleeding [N15]                | | Hb trend    (band 12.0-15.5 F)          | |
| |                                          | |   .   .   .   o   Improving             | |
| | form: needs your input                   | | Calpro      (target < 50)               | |
| | Hb [   ] calpro [   ]                    | |   .   .   .   o   Improving             | |
| | stools/day [  ] bleeding [y/n]           | | Stools/day                              | |
| | [ Submit results ]                       | |   .   .   .   o   ? Not entered         | |
| |                                          | |                                         | |
| | Assessment: PARTIAL RESPONSE             | |                                         | |
| | - calpro down 55% [N14]                  | |                                         | |
| | Continue Tier 2; recheck day [n]         | |                                         | |
| | [ Renew prescription ]                   | |                                         | |
| +------------------------------------------+ +-----------------------------------------+ |
+------------------------------------------------------------------------------------------+
```

- Verdicts: ✓ Responding, ◐ Partial, ✕ Not responding, each with numbered reasons and cited nodes.
- **Grounded or silent applies here too (R-02):** every verdict threshold (e.g. the calprotectin fall that counts as a response), every reference band (e.g. Hb by sex) and every target (e.g. calprotectin) comes from a cited node in the knowledge pack: response-criteria nodes hung off each treatment tier, and reference ranges on each metric node. The numbers in the diagram are placeholders.
- When a criterion has no node, the screen shows the trend but no verdict: "No grounded response criterion for this measure", with ⊘ and "Suggest adding it". A verdict is never computed from rules outside the pack, and nothing ungrounded is counted as grounded in the benchmark.
- **Content work this adds (R-02):** authoring cited response-criteria and reference-range nodes for each UC and Crohn's treatment tier joins the content due by Nov 2 (alongside intent-backlog.md IB-02 and IB-08).
- Trend charts show one line per measure, a labelled target band with its node chip, and a status tag in words (never colour alone).
- **Accessibility:** h2 "Follow-up chat" and "Timeline"; landmarks header, main, complementary (patient card); keyboard entry point is the results form's first field; each chart has a text summary.

### S7 — Session history and audit (screen 16)

```text
+------------------------------------------------------------------------------------------+
| [B] Brahma   Patients | History | Knowledge | Benchmark   [IBD v1.3] Dr.Maya             |
+------------------------------------------------------------------------------------------+
| Decision support, not diagnosis. Synthetic patients only.                                |
+------------------------------------------------------------------------------------------+
| +------------------------------------------+ +-----------------------------------------+ |
| | Session history (h2)                     | | S-0143 | Dr. Maya | IBD v1.3 (h2)       | |
| | [ search sessions        ]               | | UC pancolitis E3 severe -> T2           | |
| | [All][Answered][Needs data]              | | [Replay on canvas] [Export]             | |
| | [Out of knowledge]                       | |                                         | |
| |                                          | | 1 INPUTS: quote + finding chips         | |
| | > S-0143 29 Oct 10:42                    | | 2 PLAIN-LANGUAGE WHY: ...               | |
| |   UC E3 severe -> Tier 2                 | | 3 PATH WALKED:                          | |
| |   [Answered][IBD v1.3]                   | |   N1-3 > N4 > N5-8 > N9 > N10           | |
| |   S-0139 27 Oct                          | |   > N12 > N13 > N14-18                  | |
| |   [Needs more data]                      | | 4 ANSWER AS GIVEN (bullets)             | |
| |   S-0131 22 Oct                          | | 5 SOURCES USED: source | nodes |        | |
| |   [Out of knowledge]                     | |   version at time                       | |
| |                                          | | Edits, explores, overrides              | |
| |                                          | | Record is immutable                     | |
| +------------------------------------------+ +-----------------------------------------+ |
+------------------------------------------------------------------------------------------+
```

- Shows inputs, plain-language why, path walked, answer as given, sources with the version at the time; explored branches marked "explored, not acted on".
- **Accessibility:** h1 "Session history" (visually h2 per panel), h2 session title; landmarks header, nav, main, complementary (session list); keyboard entry point is the session search field; list items are links.

### S8 — Knowledge update and versions (screen 17)

```text
+------------------------------------------------------------------------------------------+
| [B] Brahma   Patients | History | Knowledge | Benchmark   [IBD v1.3] Dr.Maya             |
+------------------------------------------------------------------------------------------+
| Decision support, not diagnosis. Synthetic patients only.                                |
+------------------------------------------------------------------------------------------+
| +------------------------------------------+ +-----------------------------------------+ |
| | Suggest a change (h2)                    | | Proposed version v1.3 -> v1.4           | |
| | Node [N13 Tier 3 Biologics v]            | | (1) Proposed (2) Review (3) Live        | |
| | Source (o) Link ( ) Upload               | | BEFORE v1.3   | AFTER v1.4 draft        | |
| | [ https://...           ]                | | Tier 3 ...    | Tier 3 ... +            | |
| | Section/page [ ]                         | |               | [your change]           | |
| | What should change [      ]              | | Affects 1 node; past sessions           | |
| | Comment (why) [           ]              | | keep v1.3                               | |
| |                                          | |                                         | |
| | [ Submit as v1.4 proposal ]              | |                                         | |
| +------------------------------------------+ +-----------------------------------------+ |
+------------------------------------------------------------------------------------------+
| Version history (h2): version | status | date | by | change | comment                    |
| v1.3 Live | v1.2 Superseded | v1.1 Superseded | v1.0 Superseded                          |
+------------------------------------------------------------------------------------------+
```

- Minimum form of the update layer (scope-document.md, Cut Order): a change becomes a proposed version with a comment; the reviewer queue and the background updater are out of v1.
- **Accessibility:** h2 "Suggest a change", "Proposed version", "Version history"; landmarks header, nav, main; keyboard entry point is the "Node to change" select; the stepper exposes the current step as text.

### S9 — Benchmark (screen 18)

```text
+------------------------------------------------------------------------------------------+
| [B] Brahma   Patients | History | Knowledge | Benchmark   [IBD v1.3] Dr.Maya             |
+------------------------------------------------------------------------------------------+
| Decision support, not diagnosis. Synthetic patients only.                                |
+------------------------------------------------------------------------------------------+
| Grounding benchmark (h1)        [SAMPLE DATA - replace with real run]                    |
| [Cases 20] [With graph 98.7%] [Plain model 39.3%] [Target >= 95%: PASS]                  |
|                                                                                          |
| Overall grounded share   with graph ======================== 98.7%                       |
|                          plain      ==========               39.3%                       |
|                          (dashed marker at 95%)                                          |
|                                                                                          |
| Per case (h2)   filter: [All 20] [IBD: UC] [IBD: Crohn] [Urology stub]                   |
| Case | Specialty | Recs | bar graph vs plain | Graph | Plain | Result                    |
| B-01 | IBD UC    | 12   | ======== / ===     | 100%  | 42%   | Pass                      |
| B-05 | IBD Crohn | 12   | =======  / ===     | 92%   | 33%   | Below 95%                 |
+------------------------------------------------------------------------------------------+
```

- Your wireframe shows 16 IBD + 4 urology cases. Per Q7 the IBD cases span both UC and Crohn's, so the filter splits IBD into UC and Crohn's.
- Pass is ≥ 95% of recommendations linked to a node and its source, against the same model with no graph (intent-backlog.md IB-09).
- **Accessibility:** h1 "Grounding benchmark", h2 "Per case"; landmarks header, nav, main; keyboard entry point is the case filter; bars carry their numbers as text, and Pass / Below 95% is a word, not just a colour.

## Accessibility (all screens)

WCAG 2.1 AA basics: status never by colour alone (symbol + word), text contrast ≥ 4.5:1, targets ≥ 44 px, real buttons and labelled inputs, full keyboard navigation including map zoom and the card toggle (Q6; handover, Accessibility).

## Scope check against the backlog

| Screen | Backlog item | Note |
|--------|--------------|------|
| S1, S1a | IB-06 | Tour and disclaimer added by Q8 |
| S2 | IB-06 | Patients landing (new; structural only) |
| S3, S4 | IB-03, IB-06, IB-07 | Explore and edit treatment added by Q8 |
| S5 | — | New: prescription, added by Q8 |
| S6 | — | New: follow-up with trends, added by Q8 |
| S7 | IB-04 | |
| S8 | IB-10 | Minimum form |
| S9 | IB-09, IB-11 | Includes the urology stub |

## Assumptions & Open Questions

- [assumption] Prescription, follow-up, explore, edit treatment and the tour fit into the Nov 2 date alongside the approved scope; the schedule had no slack before they were added (Q8; scope-document.md, Scope-vs-Timeline Check).
- [assumption] Patient names on cards are invented and labelled "synthetic"; no real identifiers appear anywhere.
- Open (from your handover): reference ranges and their sources; Tier 2 entry for severe UC; second sign-off for edited treatments; pinch zoom and pan; the "Brahma" name check; prescription format against NMC guidance; ICD-10 K51.0; registration verification.
