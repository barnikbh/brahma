# Brahma — Design Handover

Oct 29, 2026 · Ardhra

## Overview

Brahma (working title: Clinical Decision Graph) is a chat-first decision-support workspace for specialist doctors. Every answer comes from a curated knowledge graph and cites its node and source. The first pack is IBD; urology is a stub that shows the model generalises. It is built for the Meta Global AI Developer Hackathon (Theme 2, Indie track), due 4 Nov 2026.

**Wireframes:** [Brahma — Wireframes](https://claude.ai/artifact/9P9tgvea8bc5hBj5JoBKfr), an interactive canvas. Play any artboard to click through it.

**Live handover doc:** [Brahma — Design Handover](https://claude.ai/artifact/UBRupoeUnN76JNsJkdEuVL) (this file is an export of it on 29 Oct 2026).

**Primary user:** Dr. Maya, consultant gastroenterologist. She uses it live in a consult (it must be scannable in seconds) and before or after one (deeper review).

**Design principles**

- **Grounded or silent.** No line appears without a graph node and a source. When the graph can't answer, the UI says so and never guesses.
- **Chat first.** The doctor talks to the agent. When the agent needs input, it asks with a form inside the chat.
- **The map mirrors the chat.** Selecting a chat line highlights its node, and selecting a node highlights the line.
- **Scannable live, deep on demand.** Detail sits one click away.
- **Always visible:** "Decision support, not diagnosis", the knowledge version in use, and the patient card.
- **Synthetic data only** in the demo build.

## Brand: name and colour

The product is **Brahma**: "Brahma" as a serif wordmark, with "Clinical decision graph" as the descriptor beneath it. The colour scheme is **indigo + sage**. Indigo carries brand and action; sage carries calm surfaces. Neither colour is ever used to mean a result.

| Token | Hex | Use |
| --- | --- | --- |
| Indigo 900 | #312E81 | Wordmark, primary buttons, active nav, agent avatar, signed stamp |
| Indigo 700 | #4338CA | Walked path, selection, citation chips, links |
| Indigo 50 / 200 | #EEF2FF / #C7D2FE | Used-node fill, selection halo, completed steps |
| Sage page | #F1F4F0 | Page background |
| Sage note | #E6EEE4 on #BFCDBB, text #2F4034 | Disclaimer bar |
| Ink / quiet | #171717 / #525252 | Body text / secondary text |
| Fuchsia 700 | #A21CAF | Exploring a side branch (only meaning) |
| Result red / green / amber | #B91C1C / #15803D / #B45309 | Out of range / normal / test needed (only these meanings) |

**Rules**

- Brand indigo never stands for a result. Red, green and amber are kept for results and status.
- Exploring uses fuchsia so it can't be confused with the indigo walked path.
- Wordmark and screen headings use Georgia (serif); everything else uses Inter.
- The agent speaks as "Brahma" in the chat; its avatar is the indigo "B" mark.
- Name check: Brahma is a deity's name and other brands already use it. Do a trademark search and a cultural-sensitivity check before launch (see Open questions).

## Screens and flow

The demo walk runs Sign-in → Patients → Workspace (chat + map) → History. Knowledge and Benchmark sit in the top nav. Every workspace state below is the same component with a different starting state, so a change to the workspace carries through all of them.

| Artboard | Screen / state | What it must show |
| --- | --- | --- |
| 1 | Sign-in | Demo account picker (Dr. Maya, demo urologist); disclaimer |
| 1b | Patients landing | Search existing patients (case ID, finding, diagnosis); "+ Create new patient" |
| 2 | Workspace · new patient | Empty patient card; agent greeting; composer is the input |
| 3a | Confirm what was understood | Agent read-back form with editable finding chips |
| 3b | Working | Progress in chat; path lights up on the map step by step |
| 3c | Needs more data | Tests marked ? on the map; results form in chat |
| 3d | Answered | Cited pathway in chat; full path on the map |
| 3e | Treatment detail | Node panel with suggested drug, route, dose, frequency, duration, checks |
| 3f | Out of knowledge | "No grounded answer"; nothing guessed |
| 3g | Error | Plain message, Retry; inputs kept |
| 3h | Exploring a side pathway | Infectious colitis branch in magenta; main plan unchanged |
| 3i | Edit treatment | Edit form in chat, prefilled from the suggestion; patient card expanded |
| 4 | Session history / audit | Inputs, path walked, sources, answer, plain-language why |
| 5 | Knowledge update + versions | Link a source, describe a change, review steps, version history |
| 6 | Benchmark | 20 synthetic cases; graph vs plain model; 95% target |

**Added since:** 1a First sign-in (disclaimer + tour) · 7 Generate prescription · 8 Follow-up visit + trends. Sign-in now goes to 1a on first use, then to Patients.

**Navigation rules**

- A case is entered from the Patients landing and left with **Exit case**. There is no "New patient" inside a case.
- Sign-in lands on Patients. The top nav tab is **Patients**, not Consult.

## Patient card

The patient card sits at the top of the workspace and stays visible while the page scrolls (sticky). Collapsed is the default; the doctor expands it with one button.

| State | Shows |
| --- | --- |
| Collapsed (default) | Name · age · sex · weight · case ID; chips for first comorbidity (+N), allergy (always red with ⚠), "+N more" |
| Expanded | Adds sex (labelled "sets reference ranges"), weight ("used for mg/kg doses"), pregnancy status, allergies, full comorbidities, current medication |
| New case, nothing captured | Dashed placeholder: "Describe the patient in the chat; details fill in here" |

**Requirements**

- The card is never hidden or scrolled away inside a case.
- When details overflow one line, the card shrinks to the collapsed row and offers **Expand ▾ / Collapse ▴** (`aria-expanded` set).
- Allergies always show in the collapsed row, in red, with an icon and the word "Allergy".
- **Edit details** posts a patient-details form into the chat (sex, weight, comorbidities, allergies). The doctor can also say it in the chat ("she's 62 kg", "patient is male"), which opens the same form prefilled.
- Saving the form updates the card, the reference ranges and any weight-based doses straight away, and the chat confirms what changed.
- Demo data is synthetic: names such as "Lakshmi R." are invented and labelled "synthetic" next to the case ID.

## Chat-first interaction

The doctor's main input is a chat with the agent. Case history, new results, questions, explore requests and treatment edits all go through the composer. When the agent needs structured input, it posts a form as one of its own messages in the thread.

**Agent forms in the chat**

| Form | Triggered by | Fields | On submit |
| --- | --- | --- | --- |
| Confirm findings | First patient message | Editable chips: kind, name, value, unit; add / remove | Walks the graph |
| Needs more data | Graph can't refine further | Stool culture, colonoscopy + biopsy, extent, severity | Refines to sub-type, or stops if out of knowledge |
| Edit treatment | "Edit" in the node panel, or chat ("change dose to 40 mg") | Drug, route, dose, frequency, duration | Applies the edit; logs it against the suggestion |
| Patient details | "Edit details" on the card, or chat ("patient is male") | Sex, weight, comorbidities, allergies | Updates card, ranges, doses |

**Requirements**

- An open form has a dark 2 px outline and the label "form · needs your input".
- Once submitted, the form shrinks to a one-line summary and the doctor's answer appears as their own message, so the thread is the case record.
- Actions taken on the map (explore, edit treatment) also post a line into the chat, e.g. "Explore: Infectious colitis (from the map)".
- Free text that changes the case ("also reports joint pain for 2 months") is added to the history. The agent then offers "Review findings and re-walk".
- The composer hint lists what can be typed: history, results, "explore …", "change dose …".

## Graph view (network map)

The right panel is a node-and-link network map (option E, chosen from five explorations). Columns are walk stages, so the layout never reshuffles between sessions.

**Layout:** Findings → Diagnosis → Tests → Sub-type → Treatment → Monitor · watch. Each node is a fixed 100 × 72 box with three rows: status badge + type + citation (N1–N18), short label, result chip.

| Element | Style | Meaning |
| --- | --- | --- |
| Edge, solid indigo 2.5 px | Path walked | Used in this session |
| Edge, thin grey | Bypassed | e.g. Tier 1 when the patient enters at Tier 2 |
| Edge, grey dashed | Not taken | Considered alternative |
| Edge, magenta dashed | Exploring | Side branch the doctor opened |
| Node, indigo border | Used | On the path |
| Node, thick indigo border + ▶ | Entry tier | Where this patient enters the treatment ladder |
| Node, indigo dashed + ? | Test needed | On the path, result not in yet |
| Node, black dashed + ⊘ | Not in this pack | Branch the graph can't answer |

**Zoom**

- Controls above the map: − / % / + / Fit / 100%. Range 40–200% in 20% steps.
- The map scrolls in both directions inside its frame when zoomed in.
- Later: pinch and ctrl-scroll zoom, plus drag to pan.

**Selection sync:** clicking a chat line selects its node and opens the detail panel; clicking a node highlights its chat line. The selected node turns solid indigo with a halo.

**Progressive reveal:** while the agent walks, nodes and edges light up in walk order. Tier edges follow the patient's entry tier.

## Results and thresholds

Every finding and test shows its result against a reference range. Sex-specific ranges are picked automatically from the patient card; the doctor never chooses them by hand.

**Result colours** (each also carries a symbol and a word, so colour is never the only cue)

| Result | Colour | Symbol | Example |
| --- | --- | --- | --- |
| Below range | Red | ↓ Low | Hb 10.2 g/dL (female range 12.0–15.5) |
| Above range | Red | ↑ High | Calprotectin 850 µg/g (< 50) |
| Abnormal finding | Red | ! | Colonoscopy: UC pattern |
| Normal | Green | ✓ Normal | Stool culture negative |
| Not yet tested | Amber, dashed | ? | Result needed |
| Planned monitoring | Grey | ◷ | Calprotectin target < [x] |

**Done vs needed:** every finding and test node carries a badge. A green filled circle with ✓ means done or tested. An amber outlined circle with ? means the test still needs doing.

**Sex-specific thresholds — requirements**

- Each metric node in the knowledge graph stores its reference range per sex where the source gives one (e.g. haemoglobin: female 12.0–15.5 g/dL, male 13.5–17.5 g/dL). Values come from the cited source, not from the UI.
- The UI reads sex from the patient card and applies the matching range automatically.
- The detail panel states which range was used and why: "12.0–15.5 g/dL (female, picked from the patient card)".
- If sex is not recorded, the widest range is used and the panel says "sex not recorded, confirm on the card".
- Changing sex on the card re-colours every affected result at once, and the chat confirms the change.
- The same rule extends to other attributes the source keys ranges on (age bands, pregnancy) — see Open questions.

## Explore alternative pathways

The doctor can open any considered-but-not-taken branch to see what it would involve, without changing the main plan. It works from the map or from the chat.

**How to start**

- **Map:** click an alternative node (e.g. Infectious colitis) → **⌖ Explore this pathway** in the detail panel.
- **Chat:** "explore infectious colitis", "what about Crohn's?", "rule out infection".

**What happens**

1. The chat logs the request and the agent replies with the branch's confirming tests and what is already known. Example: stool culture is shared with the main path and came back negative, so this branch is less likely.
2. The branch's tests and treatment appear on the map in a magenta lane, joined by magenta dashed edges. New tests carry the ? badge.
3. The agent offers **Add these tests to the plan** and **Stop exploring**.
4. The main path, summary and treatment plan stay as they are.

**Grounded or silent:** if the branch isn't in the knowledge pack (Crohn's in IBD v1.3), the agent says "Nothing grounded to explore", shows ⊘ on the node, and offers "Suggest adding this branch". It never fills the gap from model memory.

**Audit:** explored branches are saved with the session, marked "explored, not acted on" unless tests were added.

## Treatment details and editing

Clicking a treatment tier (on the map or its chat line) opens its full plan in the detail panel. Every value is a suggestion from the pack, and the doctor can edit it from the panel or the chat; both paths end in the same form in the chat.

**Fields shown for each treatment**

| Field | Example (Tier 2) | Notes |
| --- | --- | --- |
| Type | Corticosteroid | Drug class |
| Drug | Methylprednisolone | Pick from the tier's options (e.g. Hydrocortisone) |
| Route | IV | |
| Dose | [60 mg] | mg/kg drugs show the computed dose from the card's weight, e.g. Infliximab [5 mg/kg] ≈ 290 mg at 58 kg |
| Frequency | [Once daily] | |
| Duration / review | [Review response at day 3] | |
| Pre-start checks | Infection excluded first (stool culture) | Screening the source requires |
| Safety | ✓ No conflict with recorded allergy (Penicillin) | Allergy, comorbidity and interaction checks |

Values in [brackets] are wireframe placeholders. The build must take every dose, frequency and duration from the cited source.

**Edit paths**

- **Panel:** "Edit treatment" posts an Edit treatment form into the chat, prefilled with the current values.
- **Chat:** "change dose to 40 mg", "switch to hydrocortisone", "use ustekinumab" opens the same form with the change already filled in. The tier is the selected node, else inferred from the drug named.
- Changing the drug in the form resets route, dose and frequency to that drug's suggestion.

**On apply**

- Re-run allergy and weight checks; the chat reports the result.
- Mark edited fields "✎ edited" in the panel and add "✎ edited" to the chat line. The panel header changes from "Suggested by pack" to "Edited by Dr. Maya".
- Log the original suggestion, the edit and who made it in the session audit.

## Sign-in and first run

Brahma is for registered doctors only. There is no public landing page: the first screen is sign-in. A doctor's first sign-in goes through a one-time acceptance and a three-step tour before they reach Patients.

**Sign-in (artboard 1)**

- Demo build: pick a demo account (gastroenterologist or urologist). Production: hospital account / SSO, with "For registered medical practitioners only".
- Verifying the medical registration number at account creation is out of scope for the hackathon (see Open questions).

**First run (artboard 1a)**

1. **Disclaimer.** "Decision support, not diagnosis": the doctor stays responsible for every decision, prescription and order. Two required checkboxes: the responsibility statement, and synthetic patients only (demo). "Accept and continue" stays disabled until both are ticked. The acceptance is logged once with the date and knowledge version.
2. **Talk to Brahma.** Type the case naturally; Brahma reads it back and asks with in-chat forms.
3. **Read the map.** Legend for ✓ ? ↓ ↑ !, normal, walked path, exploring; ranges follow the patient's sex.
4. **Check, edit, sign.** Citation chips open sources; treatments are editable suggestions; prescriptions are signed and audited.

- Steps 2–4 offer "Skip the tour". The tour can be replayed from Help.
- If the disclaimer text or the knowledge pack changes materially, the doctor accepts again.

## Follow-up visit and trends

A follow-up visit opens the same patient, asks for today's results in the chat, plots them against earlier visits, and says whether the pack's criteria point to continue, taper or escalate (artboard 8). On the Patients list it shows as "◷ Follow-up due today".

**Layout**

- Patient card, as in the workspace, plus the current treatment chip and a visit chip ("Visit 3 · day 14 · 12 Nov 2026").
- **Left:** follow-up chat. Brahma names the response measures and their nodes, then posts a results form: Hb, calprotectin, stool frequency, rectal bleeding.
- **Right:** treatment timeline (diagnosis → day-3 check → visit 2 → today), then one trend chart per measure.

**Trend charts**

- One line per measure across visits, today's point hollow until entered.
- A green band shows the target or normal range, labelled ("female 12.0–15.5", "target < 50"). Hb uses the sex from the patient card.
- A status tag with symbol and words: ✓ In range · ↓/↑ Improving · ! Not improving · ? Not entered.

**Assessment** (demo logic; real thresholds come from the source)

| Verdict | Demo rule | Next step | Prescription action |
| --- | --- | --- | --- |
| ✓ Responding | Calprotectin < 250, ≤ 3 stools/day, no bleeding | Continue; start taper and maintenance per source | Update prescription (taper) |
| ◐ Partial response | Calprotectin down ≥ 50% or ≤ 5 stools/day | Continue Tier 2; recheck at day [n] | Renew current prescription |
| ✕ Not responding | Neither | Escalate to Tier 3; TB and hepatitis B screening | Draft Tier 3 prescription |

Each verdict lists its reasons with numbers, cites its nodes, and is saved to the audit as a new visit.

## Generate prescription

From an answered case, the doctor generates a prescription drafted from the plan, reviews and edits it, runs safety checks, and signs it into a PDF (artboard 7).

**Entry points:** "℞ Generate prescription" in the chat summary; typing "generate prescription" in the chat; the follow-up assessment.

**Editor (left)**

- One card per medicine: include toggle, generic name in CAPITALS, source chip (node ID, "Card" for existing medication, "Manual" when added by hand), form · route, dose, frequency, duration, and instructions for the patient.
- Pre-filled from the treatment plan, including any edits made in the case, plus the patient's current medication from the card.
- Fields that still hold [placeholders] get a dashed amber outline.
- "+ Add medicine" or the chat ("add pantoprazole 40 mg once daily"); manual lines are labelled "not from the pack".

**Safety checks** (each with ✓, ? or !, plus words)

| Check | Source of truth | Blocks signing? |
| --- | --- | --- |
| Allergy cross-reaction | Patient card allergies | Yes, when a conflict is found |
| Pregnancy | Patient card | Yes, when a medicine is contraindicated (production) |
| Interactions | Pack interaction nodes | No; flagged for review |
| Duplicate class | Prescription lines | No; flagged |
| Doses from source | Pack values | Production: yes while placeholders remain; demo: warning |

**Preview (right):** doctor's letterhead (name, qualifications, registration no., clinic); patient name (synthetic), age/sex/weight, case ID, date, allergy in red; diagnosis with ICD-10 code; ℞ lines; investigations, advice, warning signs, follow-up dates; footer with knowledge version and audit ID. Demo builds carry a "DEMO · SYNTHETIC PATIENT" watermark.

**Sign:** a responsibility checkbox is required. Then "Sign and generate PDF" stamps an e-signature with time and prescription ID, saves it to the case audit, and offers Download PDF, Print, Share with patient (later), and Void and re-issue.

## End-to-end coverage

The core journey is designed end to end: sign in → accept → find or create a patient → consult in chat → refine → explore → edit treatment → prescribe → follow up → audit. The pieces below are still needed before a full product; none blocks the hackathon demo.

| Area | What it covers | Priority |
| --- | --- | --- |
| Close case / visit summary | End the consult; one-page summary for the patient file (PDF), signed; marks the case "closed" or "follow-up scheduled" | High |
| Settings & profile | Doctor details for the letterhead, registration no., signature, default specialty pack, notification and session-timeout settings | High |
| Specialty pack switcher | Switch between IBD and Urology (stub); show the pack and version on the patient and every answer | High |
| Help & "how grounding works" | Replay the tour, glossary of icons, explanation of sources and versions, contact support | Medium |
| Knowledge reviewer queue | Reviewers approve or reject proposed versions; diff, comments, publish; notify proposer | Medium |
| Notifications | Follow-up due, results arrived, knowledge version updated, proposal approved | Medium |
| Session safety | Auto-lock after inactivity, re-auth to sign prescriptions, sign-out from all devices | Medium |
| Offline / slow network | What still works without the service; queued messages; clear banners | Low |
| Tablet layout | Chat and map as tabs; sticky patient card; larger hit targets | Low |
| Empty and edge states | No patients yet, search no results, duplicate patient, merge case | Low |

## States, accessibility, data rules and open questions

**States every workspace must handle:** empty (new case), confirm, working, needs more data, answered, exploring, editing treatment, out of knowledge (no entry match, branch not in pack, positive stool culture), error with retry.

**Accessibility (WCAG 2.1 AA basics)**

- Status is never shown by colour alone: every colour pairs with a symbol (✓ ? ↓ ↑ ! ⊘ ⌖ ◷) and a word.
- Text contrast ≥ 4.5:1, including small grey labels and coloured result chips.
- Touch targets ≥ 44 px; real buttons, links and labelled inputs; map nodes carry an `aria-label` with status and result.
- Fully keyboard navigable, including zoom and the card toggle.

**Data rules**

- Synthetic patients only in the demo; names and IDs are invented and labelled "synthetic".
- "Decision support, not diagnosis" and the knowledge version appear on every screen.
- Every edit, explore and override is written to the session audit.

**Open questions**

- [ ] Confirm reference ranges and their sources: Hb by sex, calprotectin cut-off, and any age- or pregnancy-specific ranges.
- [ ] Confirm the treatment ladder entry logic with a clinician (severe UC enters at Tier 2).
- [ ] Real names on patient cards break the brief's "no real identifiers" rule. Decide how a production build handles identifiable data.
- [ ] Should edited treatments need a second sign-off before they count as the plan?
- [ ] Should pinch zoom and drag to pan be in the hackathon build?
- [ ] Tablet support: in or out for v1?
- [ ] Run a trademark search and cultural-sensitivity check on the name "Brahma" before public use.
- [ ] Confirm the prescription format against Indian rules: generic names in capitals, required doctor details and registration number (NMC guidance).
- [ ] Confirm the ICD-10 code shown for UC pancolitis (K51.0).
- [ ] Decide how a doctor's medical registration is verified at account creation.
