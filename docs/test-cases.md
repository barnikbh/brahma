# Test cases

Synthetic patients for testing every feature by hand. Decision support, not diagnosis. Every patient here is invented.

## Reset and seed

Stop the server first (Ctrl+C in its terminal), then from the project folder:

```bash
.venv/bin/python scripts/seed_test_cases.py
```

This deletes the old database and its cases (no migration) and creates the patients below. Start the server again afterwards. Each patient's chat opens with a note saying what to type first.

Model: the live Meta model (`.env`) answers every case. The offline `recorded` provider (see README) only knows the demo text and the T03/T04 follow-ups, so only cases marked *offline* walk without a key.

To keep your own database, seed a separate one and serve it on another port:

```bash
.venv/bin/python scripts/seed_test_cases.py --db data/test-cases.db
```

```bash
set -a && source .env && set +a && BRAHMA_DB_PATH=data/test-cases.db BRAHMA_PORT=8001 .venv/bin/python -m brahma.server
```

## Run every case automatically

`scripts/live_test_cases.py` plays each case's steps through the same API the web app uses, checks the expected results and writes `results/live-test-cases.md` (what the model returned and which screen component draws it). The walked cases stay in the database to open in the app.

```bash
BRAHMA_REHEARSAL_BASE=http://127.0.0.1:8001 .venv/bin/python scripts/live_test_cases.py
```

## Cases

| ID | Case | Covers | Profile |
|---|---|---|---|
| T01 | Demo walk: acute severe UC *(offline)* | US3.1-US3.5, US4.1, US7.1, AC3.2.1, AC3.2.2 | Dr. Maya |
| T02 | Day-3 review: unmet, then met *(offline)* | Day-3 review (Nov 4), criterion If met links | Dr. Maya |
| T03 | Follow-up after anti-TNF failure, then day-3 review *(offline)* | Follow-up turn, US3.2 history, today's review fix | Dr. Maya |
| T04 | Steroid-refractory follow-up *(offline)* | Follow-up turn, surgical escalation | Dr. Maya |
| T05 | Edit a suggested treatment *(offline)* | US4.2 (AC4.2.1, AC4.2.2) | Dr. Maya |
| T06 | Explore an alternative pathway *(offline)* | US3.6 (AC3.6.1, AC3.6.2) | Dr. Maya |
| T07 | Findings: unit conversion, invalid value, late details | US3.1 (AC3.1.2, AC3.1.3) | Dr. Maya |
| T08 | Partial test results *(offline)* | US3.3 (AC3.3.1, AC3.3.2) | Dr. Maya |
| T09 | Mild ulcerative proctitis | Tier 1 path (mesalamine) | Dr. Maya |
| T10 | High CRP typed at presentation | Safety: a presenting CRP never skips a tier | Dr. Maya |
| T11 | Crohn's: mild ileal | AC3.2.5 (Crohn's at the same depth) | Dr. Maya |
| T12 | Crohn's: moderate colonic, weight missing | AC4.1.2 (weight-based dose), AC3.1.3 | Dr. Maya |
| T13 | Crohn's: penetrating | Crohn's watch-outs (abscess) | Dr. Maya |
| T14 | Safety checks on the patient card *(offline)* | US4.1 (AC4.1.3), BR4 safety | Dr. Maya |
| T15 | Out of knowledge | US3.4 (AC3.4.1) | Dr. Maya |
| T16 | Case pinned to an older pack version *(offline)* | US2.1 (AC2.1.3), FR1.7 | Dr. Maya |
| T17 | Care loop: prerequisites before a biologic *(offline)* | Care-graph redesign: requires edges, To do first, results scoped to a treatment | Dr. Maya |
| T18 | Care loop: symptom asserted, recurring test *(offline)* | Care-graph redesign: if_present edges, Patient has this now, Watch for to Now | Dr. Maya |
| U01 | Urology: small distal stone | US9.1 (AC9.1.1, AC9.1.2) | Demo urologist |
| U02 | Urology: large stone | US9.1, conditions that block a tier | Demo urologist |

## T01 · Demo walk: acute severe UC

Card: 34, female; 58 kg.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Type the start text and confirm the findings.
2. Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; then extent **E3**, severity **severe**.
3. Click a cited line, then its node on the map; open Hydrocortisone.
4. Press Choose this option.
5. Open the why panel.

Expect:

- Map lights up column by column; tests show ? until answered.
- Pathway reaches ulcerative colitis, pancolitis, severe, with Tier 2 IV steroids as Start here.
- Summary shows 0 ungrounded (1 is possible on the live model), the pack IBD 1.2 and the model.
- Tier 2 drugs are grey Options; choosing one marks it Chosen, lights its monitoring blue and shows the Now on card.
- Every why sentence has node chips.

## T02 · Day-3 review: unmet, then met

Card: 34, female; 60 kg.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Walk as in T01 (Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; then extent **E3**, severity **severe**.)
2. Open the monitor node Day 3 on IV steroids: CRP above 45 mg/L.
3. Record 20.
4. Record 60.
5. Try nan, -5 and abc.
6. Open Toxic megacolon.

Expect:

- The criterion panel shows If met -> UC Tier 3.
- 20: says the value does not meet the criterion and the plan is unchanged; no new walk.
- 60: a new review walk; UC Tier 3 becomes Start here; still 0 ungrounded.
- nan, -5 and abc are refused with an error; nothing is recorded.
- Toxic megacolon shows Where it leads: Emergency colectomy triggers.

## T03 · Follow-up after anti-TNF failure, then day-3 review

Card: 34, female; 64 kg.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Walk as in T01 (Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; then extent **E3**, severity **severe**.)
2. Type: Remicade failed. steroids work. Suggest alternate treatment plan (press Enter).
3. Then record day-3 CRP 60 on the CRP criterion.

Expect:

- Brahma notes the history (Remicade mapped to infliximab).
- The plan moves to UC after anti-TNF failure; Infliximab shows Tried.
- After the CRP 60 review, infliximab is still Tried and never suggested again.

## T04 · Steroid-refractory follow-up

Card: 34, female; 66 kg.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Walk as in T01 (Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; then extent **E3**, severity **severe**.)
2. Type: Infliximab stopped working and steroids did not work

Expect:

- History reads infliximab lost response; corticosteroid no response.
- Watch-outs include the steroid-refractory surgical review.

## T05 · Edit a suggested treatment

Card: 34, female; 55 kg.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Walk as in T01 (Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; then extent **E3**, severity **severe**.)
2. Open Methylprednisolone and type: change dose to 40 mg
3. Apply the edit, then reload the page.

Expect:

- An Edit treatment form opens with 40 mg filled in.
- After applying: the field shows edited, the panel says Edited by Dr. Maya, and the marker survives the reload.
- History export shows the original, the edit and who made it.

## T06 · Explore an alternative pathway

Card: 34, female; 62 kg.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Walk as in T01 (Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; then extent **E3**, severity **severe**.)
2. Type: explore infectious colitis
3. Press Stop exploring.

Expect:

- Infectious colitis appears in a separate dashed lane; the main plan is unchanged.
- Stop exploring closes the lane; the audit marks it explored, not acted on.

## T07 · Findings: unit conversion, invalid value, late details

Card: 34, female; no weight.

Type first: `34-year-old woman, bloody stool 6 months, Hb 102 g/L, calprotectin 850 µg/g`

Steps:

1. Look at the Hb chip before confirming.
2. Change the Hb value to abc.
3. Put it back to 10.2, confirm, and while the needs-data form is open type: she's 62 kg, also joint pain for 2 months

Expect:

- The chip reads Hb 10.2 g/dL (entered 102 g/L).
- abc marks the chip invalid and the walk cannot start.
- The patient card updates to 62 kg, the chat confirms, and Review findings and re-walk is offered.

## T08 · Partial test results

Card: 34, female; 61 kg.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Confirm the findings.
2. In the needs-data form fill only stool culture (negative); leave colonoscopy empty and submit.

Expect:

- The form names the tests it needs; the map marks them ?.
- Colonoscopy stays ? not yet tested; the walk ends as Needs data at suspected IBD.

## T09 · Mild ulcerative proctitis

Card: 29, male; 78 kg.

Type first: `29-year-old man, bloody stool 2 months, calprotectin 120 µg/g`

Steps:

1. Needs data: stool culture negative, colonoscopy ulcerative colitis; extent E1, severity mild.

Expect:

- Reaches ulcerative proctitis, mild, with UC Tier 1 mesalamine.
- Watch the mesalamine line: the pack stores exactly 2 g, so another dose is held back as ungrounded.

## T10 · High CRP typed at presentation

Card: 41, male; 72 kg.

Type first: `41-year-old man, bloody stool 3 months, stool frequency 4 per day, CRP 60 mg/L, Hb 11.8 g/dL`

Steps:

1. Needs data: stool culture negative, colonoscopy ulcerative colitis; extent E3, severity severe.

Expect:

- CRP 60 is above the day-3 threshold of 45, yet the entry stays UC Tier 2.
- Tier 3 rescue is only a later planned step: only a day-3 result recorded on the criterion (T02) can move the entry.

## T11 · Crohn's: mild ileal

Card: 26, male; 75 kg.

Type first: `26-year-old man, abdominal pain 4 months, weight loss 3 kg, calprotectin 200 µg/g`

Steps:

1. Needs data: stool culture negative, colonoscopy Crohn's disease; location L1, behaviour B1, severity mild.

Expect:

- Reaches ileal Crohn's with Crohn's Tier 1 oral budesonide.

## T12 · Crohn's: moderate colonic, weight missing

Card: 33, female; no weight.

Type first: `33-year-old woman, abdominal pain and diarrhoea 5 months, weight loss 4 kg, calprotectin 350 µg/g`

Steps:

1. Needs data: stool culture negative, colonoscopy Crohn's disease; location L2, behaviour B1, severity moderate.
2. Open Infliximab 5 mg/kg IV.
3. Type: she's 62 kg, then open Infliximab again.

Expect:

- Reaches Crohn's Tier 2 anti-TNF.
- With no weight, the dose says the weight is needed instead of guessing.
- After 62 kg: 310 mg, shown as 5 mg/kg × 62 kg = 310 mg.

## T13 · Crohn's: penetrating

Card: 31, female; 59 kg.

Type first: `31-year-old woman, abdominal pain 4 months, weight loss 6 kg, calprotectin 500 µg/g`

Steps:

1. Needs data: stool culture negative, colonoscopy Crohn's disease; location L3, behaviour B3, severity severe.

Expect:

- Reaches penetrating Crohn's; watch-outs include the abscess path.

## T14 · Safety checks on the patient card

Card: 34, female; 70 kg; allergies: penicillin; medication: methylprednisolone; pregnancy: pregnant.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Walk as in T01 (Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; then extent **E3**, severity **severe**.)
2. Open Hydrocortisone and read its safety checks.

Expect:

- Allergy: No cross-reactivity with recorded allergies, citing the penicillin allergy node.
- Pregnancy: ? Not checked: no grounded safety data (never no conflict).
- Duplicate class: conflict, because methylprednisolone on the card is another corticosteroid.
- Interaction: ? Not checked where no interaction node applies.

## T15 · Out of knowledge

Card: 28, male; 70 kg.

Type first: `28-year-old man, headache with visual aura for 2 days`

Steps:

1. Confirm the findings.
2. Press Suggest adding this branch.

Expect:

- No grounded answer with the ⊘ mark; no diagnosis or treatment line.
- Suggest adding this branch opens the Knowledge screen.
- History filter Out of knowledge lists this session.

## T16 · Case pinned to an older pack version

Card: 34, female; 60 kg; pinned to IBD 1.0.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Open the case before typing anything.
2. Walk as in T01 (Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; then extent **E3**, severity **severe**.)
3. Type: Remicade failed. steroids work.
4. Press Re-walk on the banner, then type the same follow-up again.

Expect:

- The banner says a newer version is available; the pack chip says IBD 1.0.
- On 1.0 the follow-up gives No grounded answer (1.0 has no anti-TNF failure path).
- After re-walk on IBD 1.2 the same follow-up gives the post-anti-TNF plan.

## T17 · Care loop: prerequisites before a biologic

Card: 34, female; 64 kg.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Walk as in T01 (Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; then extent **E3**, severity **severe**.)
2. Type: Remicade failed. steroids work. Suggest alternate treatment plan (press Enter).
3. Click Vedolizumab (a click only opens the panel), then press Choose this option.
4. Open Latent tuberculosis screen: it is To do first. Pick negative, Record result.
5. Open Hepatitis B screen and record negative.
6. Now click Ustekinumab and Choose this option.

Expect:

- Choosing Vedolizumab lights both infection screens blue as To do first, with an arrow 'needs first', even if you gave screening results earlier.
- A cited note appears for the newly lit nodes; the Now on card lists To do first.
- A recorded result turns that screen Done and appears in the timeline strip.
- Choosing Ustekinumab asks for both screens again (a result counts for the treatment it was recorded for).

## T18 · Care loop: symptom asserted, recurring test

Card: 34, female; 60 kg.

Type first: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`

Steps:

1. Walk as in T01 (Needs-data forms: stool culture **negative**, colonoscopy **ulcerative colitis**; then extent **E3**, severity **severe**.) and choose Hydrocortisone.
2. Open Toxic megacolon (Watch for) and press Patient has this now.
3. Open Exclude infection at presentation and in flares and press Patient has this now.
4. Open the stool culture test that comes back Due and record a result.
5. Open CRP on intravenous steroids, record 30.

Expect:

- Monitoring and watch-out blocks never say Suggested: they read Due / Watch for.
- Toxic megacolon turns Present and Emergency colectomy triggers turns Now.
- The stool culture test returns as Due, then Done once a result is recorded.
- The focus view shows the current state; Show whole map reveals the rest.

## U01 · Urology: small distal stone

Card: 45, male; 85 kg.

Type first: `45-year-old man with renal colic since yesterday, stone size 6 mm`

Steps:

1. Sign in as Demo urologist.
2. Needs data: CT KUB ureteric stone.

Expect:

- Runs on the URO 0.1 pack chip and reaches Tier 1 observation with expulsive therapy.

## U02 · Urology: large stone

Card: 50, female; 68 kg.

Type first: `50-year-old woman with renal colic for 3 days, stone size 12 mm`

Steps:

1. Sign in as Demo urologist.
2. Needs data: CT KUB ureteric stone.

Expect:

- The 12 mm stone is over the Tier 1 size limit, so no tier is entered.

## App checks (no special patient)

### Sign in and disclaimer (US1.1, US1.2)

- Sign in as Dr. Maya: no password; name in the header.
- First sign-in: Accept and continue is disabled until both boxes are ticked.
- Decision support, not diagnosis and the pack version show on every screen.

### Patients (US2.1)

- The list opens with the T and U patients; searching a case ID finds it.
- Searching nonsense shows No patients found and Create new patient.

### History (US7.1, US7.2)

- After T01 and T15: filter by outcome, Replay on canvas (read-only map on the recorded version, chosen drug kept), Export JSON and PDF.

### Knowledge (US8.1, US8.2)

- Browse: walk nodes and edges freely.
- Update: source https://reference.medscape.com/drug/stelara-wezlana-ustekinumab-345050 plus a short note; a before/after card appears with the page cited.
- A note with no URL gets one follow-up question, never a loop.
- Sign in as Demo clinical reviewer to Approve and publish; IBD goes to 1.3 and old sessions keep their version.
