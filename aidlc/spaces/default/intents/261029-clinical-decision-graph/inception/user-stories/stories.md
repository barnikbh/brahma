# User Stories — Brahma

Upstream: `requirements.md` (FR and NFR IDs, priority and cut order), `team-practices.md`, personas in `personas.md`. Grouped by the doctor's workflow, in the demo video's order (Q1). Kept light: one story per screen or agent capability (Q2).

Priority (MoSCoW) follows `requirements.md`, Priority and Cut Order. The demo walk is US1–US3 plus US7.1.

## US1 — Sign in

### US1.1 Pick a demo profile — Must
As Dr. Maya, I want to sign in by picking my demo profile, so that every session I run is recorded under my name.
- **AC1.1.1** Given the sign-in screen, When I pick "Dr. Maya (gastroenterologist)", Then I land on Patients with my name in the header, and no password is asked.
- **AC1.1.2** Given any screen after sign-in, Then "Decision support, not diagnosis" and the pack version are visible.
- Traces: FR11.1, FR15.1. Depends on: none.

### US1.2 Accept the disclaimer and take the tour — Must (tour: Could)
As Dr. Maya, I want to accept the responsibility disclaimer once and see a short tour, so that I know what the tool is and isn't.
- **AC1.2.1** Given my first sign-in, When both checkboxes are unticked, Then "Accept and continue" is disabled.
- **AC1.2.2** Given I accept, Then the acceptance is logged once with the date and pack version, and is not asked again until the disclaimer or a pack changes materially.
- **AC1.2.3** Given the tour, When I press "Skip the tour", Then I land on Patients.
- Traces: FR11.2, FR11.3. Depends on: US1.1.

## US2 — Patients

### US2.1 Find, create or reopen a patient — Must
As Dr. Maya, I want to find an existing patient or start a new one, so that I can continue a case or begin a consult.
- **AC2.1.1** Given Patients, When I search "calprotectin", Then matching cases are listed with a status chip; When nothing matches, Then I see "No patients found" and "Create new patient".
- **AC2.1.2** Given I create a new patient, Then a case opens with a generated ID labelled "synthetic".
- **AC2.1.3** Given I reopen a case walked on v1.3 after v1.4 is published, Then it shows v1.3, its chat, map and card as I left them, and a "Newer version available: re-walk?" banner.
- Traces: FR12.1, FR12.2, FR12.3, FR12.4, FR1.7, FR15.2, NFR6. Depends on: US1.1.

## US3 — Consult walk

### US3.1 Describe the patient and confirm findings — Must
As Dr. Maya, I want to describe the patient in plain words and check what was understood, so that the walk starts from the right findings.
- **AC3.1.1** Given I type "34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g", Then Brahma posts a "Confirm findings" form with editable chips for age, symptom with duration, and both metrics with value and unit.
- **AC3.1.2** Given I enter "Hb 102 g/L", Then the chip reads "Hb 10.2 g/dL (entered 102 g/L)"; Given a non-numeric value, Then the chip is marked invalid and the walk can't start.
- **AC3.1.3** Given I say "she's 62 kg" or "also joint pain for 2 months", Then the card or history updates, the chat confirms the change, and Brahma offers "Review findings and re-walk".
- Traces: FR4.1, FR4.8, FR4.9, FR4.11. Depends on: US2.1.

### US3.2 Get a grounded, cited pathway — Must
As Dr. Maya, I want Brahma to walk the knowledge graph from the findings to a sub-type and treatment plan, so that I can see every step and where it came from.
- **AC3.2.1** Given the demo patient and results (stool culture negative, colonoscopy UC pattern, extent E3, severity severe), When the walk completes, Then the pathway reads findings → IBD → confirm and refine → "ulcerative colitis, pancolitis, severe" → Tier 2 entry → monitor → diet → watch-outs and surgery triggers, and every line has a node chip.
- **AC3.2.2** Given the answer, Then the summary shows steps, cited and "0 ungrounded", plus the pack version and model provider.
- **AC3.2.3** Given the model returns "Methylprednisolone 120 mg" citing a node that says 60 mg, Then that line is not shown and the ungrounded count goes up by one.
- **AC3.2.4** Given I submit, Then progress appears within 3 seconds, and the full pathway arrives within 60 seconds on the submission model.
- **AC3.2.5** Given a Crohn's demo case, When walked, Then it reaches a Crohn's sub-type and tiers at the same depth.
- Traces: FR1.1, FR1.2, FR1.3, FR1.4, FR1.5, FR2.1, FR2.2, FR2.4, FR2.5, FR2.6, FR4.2, FR4.3, FR4.6, FR4.10, FR14.3, FR15.1, NFR1, NFR2. Depends on: US3.1.

### US3.3 Give the test results Brahma asks for — Must
As Dr. Maya, I want Brahma to ask for exactly the tests it needs, so that I can refine the diagnosis without guessing.
- **AC3.3.1** Given the walk can't refine past IBD, Then Brahma posts a "Needs more data" form naming the tests, and the map marks them "?".
- **AC3.3.2** Given I fill only some tests, Then the rest stay "? not yet tested" and the walk goes as far as the entered results allow.
- Traces: FR4.4, FR4.11. Depends on: US3.2.

### US3.4 Be told plainly when there's no grounded answer or something fails — Must
As Dr. Maya, I want a plain "No grounded answer" instead of a guess, and a clear error with Retry, so that I can trust what is shown.
- **AC3.4.1** Given findings that match no pack (for example headache with visual aura), Then Brahma says "No grounded answer", shows ⊘, offers "Suggest adding this branch", and shows no diagnosis or treatment line.
- **AC3.4.2** Given the model provider times out, Then I see a plain message and Retry, with all my inputs kept, and the error is logged with the provider name.
- Traces: FR4.5, FR5.9, FR14.4, NFR8. Depends on: US3.2.

### US3.5 Follow the walk on the map — Must (zoom: Could)
As Dr. Maya, I want to see the part of the graph used, lit up as Brahma walks it, so that I can check the reasoning at a glance.
- **AC3.5.1** Given the workspace, Then the chat is on the left, the map on the right, and the patient card stays visible above both while I scroll.
- **AC3.5.2** Given the walk runs, Then nodes and edges light up in walk order, in fixed columns Findings → Diagnosis → Tests → Sub-type → Treatment → Monitor.
- **AC3.5.3** Given I select a chat line, Then its node is selected and its detail opens; Given I select a node, Then its chat line is highlighted.
- **AC3.5.4** Given any result, Then it shows a symbol and word as well as colour (↓ Low, ↑ High, ✓ Normal, ? Not yet tested), and I can do all of this by keyboard.
- Traces: FR5.1, FR5.2, FR5.3, FR5.4, FR5.5, FR5.6, FR5.7, FR5.8, NFR3, NFR4. Depends on: US3.2.

### US3.6 Explore an alternative pathway — Should
As Dr. Maya, I want to look at a branch I'm ruling out (for example infectious colitis), so that I can see what it would involve without changing my plan.
- **AC3.6.1** Given I say "explore infectious colitis" or pick it on the map, Then its tests and treatment appear in a separate lane, and the main plan is unchanged.
- **AC3.6.2** Given I pick "Stop exploring", Then the lane closes and the audit marks it "explored, not acted on".
- Traces: FR4.7, FR2.7. Depends on: US3.5.

## US4 — Treatment

### US4.1 See a treatment's full detail — Must
As Dr. Maya, I want to open a treatment tier and see the drug, dose, checks and source, so that I can verify it before acting.
- **AC4.1.1** Given I select Tier 2, Then the panel shows type, drug, route, dose, frequency, review point, pre-start checks, safety checks against the card, source, version and comments.
- **AC4.1.2** Given an mg/kg drug and a 58 kg patient, Then the computed dose and its formula are shown.
- **AC4.1.3** Given a patient card with a penicillin-class allergy, When I open a treatment whose drug conflicts with it under a cited allergy cross-reactivity node, Then the panel shows "! Allergy conflict" with that node's chip. Given a drug with no safety node, Then the panel shows "? Not checked: no grounded safety data" and never "no conflict".
- Traces: FR6.1, FR6.2, FR1.6. Depends on: US3.5.

### US4.2 Edit a suggested treatment — Should
As Dr. Maya, I want to change a suggested drug or dose, so that the plan fits my patient while the original stays on record.
- **AC4.2.1** Given I say "change dose to 40 mg", Then an Edit treatment form opens in the chat with the change filled in.
- **AC4.2.2** Given I apply it, Then allergy and weight checks re-run, the field shows "✎ edited", the panel says "Edited by Dr. Maya", and the audit records the original, the edit and me.
- Traces: FR6.3, FR6.4, FR6.5. Depends on: US4.1.

## US5 — Prescribe

### US5.1 Generate and sign a prescription — Could (cut first)
As Dr. Maya, I want a prescription drafted from the plan that I can check and sign, so that I don't retype what the plan already says.
- **AC5.1.1** Given an answered case, When I pick "Generate prescription", Then a draft lists each medicine with its source chip (node, Card or Manual) in a generic international format.
- **AC5.1.2** Given a medicine that conflicts with the recorded penicillin allergy class, or a line with a placeholder, Then signing is blocked; Given a drug with no safety node, Then the check shows "? Not checked" and never "no conflict".
- **AC5.1.3** Given I tick responsibility and sign, Then a PDF with "DEMO · SYNTHETIC PATIENT" is saved to the audit; Given I void it, Then it is marked VOID, kept, and a prefilled new draft opens.
- Traces: FR7.1, FR7.2, FR7.3, FR7.4, FR7.5, FR7.6, FR7.7, FR7.8, FR1.6. Depends on: US4.1.

## US6 — Follow up

### US6.1 Record a follow-up visit and see trends — Could (cut first)
As Dr. Maya, I want to enter today's results and see them against earlier visits, so that I can decide to continue, taper or escalate.
- **AC6.1.1** Given a follow-up, When I enter results, Then each measure shows a trend line with its cited target band and a status word.
- **AC6.1.2** Given cited response criteria, Then the verdict (Responding, Partial, Not responding) lists its reasons with node chips; Given a measure with no criterion node, Then the trend shows but no verdict, with "No grounded response criterion for this measure".
- **AC6.1.3** Given v1.4 was published after the case was walked on v1.3, Then the visit's audit entry records both versions.
- Traces: FR8.1, FR8.2, FR8.3, FR8.4, FR8.5, FR2.3, FR1.7. Depends on: US3.2.

## US7 — Audit

### US7.1 Every session is audited and explained — Must
As Dr. Maya, I want each session saved with its path, sources and a plain-language why, so that I can revisit and defend a decision.
- **AC7.1.1** Given a finished walk, Then the audit holds my profile, the pack version, the provider and model, my inputs, the node path, the answer and the sources with their versions.
- **AC7.1.2** Given the "why", Then every sentence has node chips, and a sentence with no node is not shown.
- **AC7.1.3** Given any attempt to change or delete an audit entry, Then it is refused; Given the app crashes mid-write, Then the last committed entry is intact.
- Traces: FR9.1, FR9.2, FR9.3, FR9.6, NFR7. Depends on: US3.2.

### US7.2 Browse, replay and export past sessions — Must (export: Could)
As Dr. Maya, I want to find a past session and replay it, so that I can show how I reached a decision.
- **AC7.2.1** Given History, When I filter "Out of knowledge", Then only those sessions show; with none, I see "No sessions yet".
- **AC7.2.2** Given I pick "Replay on canvas", Then the map shows that session's walked path on its recorded version, read-only.
- **AC7.2.3** Given I pick "Export", Then a JSON file and a readable PDF of the session download.
- Traces: FR9.4, FR9.5, FR1.7. Depends on: US7.1.

## US8 — Knowledge

### US8.1 Suggest a change or link a source — Must (source drafting: Should)
As Dr. Maya, I want to suggest a change to a node or link a new source, so that the knowledge stays current.
- **AC8.1.1** Given I pick a node, add a source URL, what should change and why, When I submit, Then a proposed version (for example v1.3 → v1.4 draft) appears with a before-and-after view.
- **AC8.1.2** Given a linked source, Then the agent drafts the node changes; Given drafted text repeats more than 25 words of the source, Then it is flagged "possible verbatim copy".
- **AC8.1.3** Given a URL that is not http(s) or points to a local address, Then it is refused with a reason; Given the submission fails, Then my input is kept.
- Traces: FR10.1, FR10.2, FR10.8, FR10.9. Depends on: US1.1.

### US8.2 Review and publish a proposed version — Must
As the clinical reviewer, I want to see what a proposal changes and publish or reject it, so that only sourced, paraphrased changes go live.
- **AC8.2.1** Given a proposal, Then I see before and after, the source passage, the proposer and their comment.
- **AC8.2.2** Given I publish, Then the pack version goes up, version history shows the change, new sessions use it, and past sessions keep theirs.
- **AC8.2.3** Given a proposal flagged as a possible verbatim copy, Then publishing is blocked until it is rewritten.
- Traces: FR10.3, FR10.4, FR10.5, FR10.6, FR10.9. Depends on: US8.1.

### US8.3 Background check of linked sources — Could
As the clinical reviewer, I want linked sources re-checked on a schedule, so that I'm told when a source has changed.
- **AC8.3.1** Given a linked source changed since the last check, When the scheduled run happens, Then a proposed version is drafted for my review.
- **AC8.3.2** Given a source can't be reached, Then it is logged and skipped, and the others are still checked.
- Traces: FR10.7. Depends on: US8.2.

## US9 — Second specialty

### US9.1 Walk a urology case — Should
As the demo urologist, I want to run a simple urology case through the same tool, so that I can see it isn't specific to IBD.
- **AC9.1.1** Given I sign in as the demo urologist and describe a urology case, Then the walk runs on the urology stub pack and the pack chip says so.
- **AC9.1.2** Given the urology pack, Then it loads through the same model as IBD, with no specialty-specific code.
- Traces: FR3.1, FR3.2. Depends on: US3.2.

## INVEST Notes

- **Independent:** each story can be built and shown on its own once its "depends on" story exists. US5.1 and US6.1 can be cut without breaking any Must story.
- **Small:** each is one screen or one agent capability. US3.2 is the largest; its acceptance criteria give the demo walk's done line.
- **Testable:** every criterion is Given/When/Then with an observable result; AC3.2.3 is the deliberately wrong citation test.

## Story Map

| Workflow step | Must | Should | Could |
|---------------|------|--------|-------|
| Sign in | US1.1, US1.2 | | (tour in US1.2) |
| Patients | US2.1 | | |
| Consult walk | US3.1, US3.2, US3.3, US3.4, US3.5 | US3.6 | (zoom in US3.5) |
| Treatment | US4.1 | US4.2 | |
| Prescribe | | | US5.1 |
| Follow up | | | US6.1 |
| Audit | US7.1, US7.2 | | (export in US7.2) |
| Knowledge | US8.1, US8.2 | (source drafting in US8.1) | US8.3 |
| Second specialty | | US9.1 | |
