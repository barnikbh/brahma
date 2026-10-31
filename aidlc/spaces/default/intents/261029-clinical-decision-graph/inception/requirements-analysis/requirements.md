# Requirements — Brahma (Clinical Decision Graph)

**Upstream:** `intent-statement.md` (problem, user, success metrics), `scope-document.md` (in/out of scope, milestones), `intent-backlog.md` (IB-01 … IB-13), `constraint-register.md` (C-T*, C-O*, C-R*, C-Q*), `wireframes.md` and `user-flow.md` (screens S1–S9, states, fixes R-01 and R-02), `team-practices.md` and `discovered-rules.md` (way of working, testing, delivery, hard rules). Answers: `requirements-analysis-questions.md` Q1–Q8.

**Depth:** Standard. **Request type:** new product (greenfield), multi-component.

## Intent Analysis

A specialist (first persona: Dr. Maya, gastroenterologist) describes a patient's symptoms and lab values and walks, with the agent, from findings to a working diagnosis, confirming tests, a precise sub-type, a tiered treatment plan, monitoring, diet and escalation triggers. Every step is grounded in a curated, versioned, cited knowledge graph and nothing comes from model memory. Each session is audited and explained. The goal is to make a doctor's tacit pathway explicit, walkable and auditable (intent-statement.md, Problem Statement), and to prove grounding with a benchmark against the same model with no graph (C-Q2). It ships as a hackathon submission: a public repo that runs locally, plus a demo video, by Nov 4, 2026, 9:00 PM ET (C-O1; team-practices.md, Deployment).

**Superseded upstream items:** this document replaces the scope document's "deployed public URL" deliverable (C-T5) and the Oct 31 "thin slice deployed" milestone. The deliverable is now the public repo plus the demo video, run locally, and the Oct 31 milestone no longer applies (team-practices.md; practices Q2, Q5, Q8). Delivery planning re-plans the dates.

## Priority and Cut Order

Every requirement group has a priority for the Nov 2 feature-complete date. **Must** items make up the minimum that still delivers the demo video: the demo walk, the workspace, the audit and the benchmark. If time runs short, items are cut in the order below, and nothing marked Must is cut (revision decision, R-01).

| Group | Priority | Note |
|-------|----------|------|
| FR1 Knowledge model | Must | |
| FR2 IBD content | Must | FR2.3 (response criteria) is cut with FR8 |
| FR3 Urology stub | Should | |
| FR4 Grounded agent | Must | FR4.7 explore is Should |
| FR5 Workspace | Must | FR5.5 zoom is Could |
| FR6 Treatment detail and editing | Should | FR6.1 detail panel is Must |
| FR7 Prescription | Could | Cut first |
| FR8 Follow-up visit | Could | Cut first, with FR7 |
| FR9 Audit and explanation | Must | FR9.5 export is Could |
| FR10 Knowledge updates | Must for FR10.1, FR10.3–FR10.6; Should for FR10.2, FR10.9; Could for FR10.7 | |
| FR11 Sign-in and first run | Must; FR11.3 tour is Could | |
| FR12 Patients | Must | |
| FR13 Benchmark | Must | |
| FR14 Model providers | Must | |
| FR15 Disclaimers | Must | |
| FR16 Repo and setup | Must | |

**Cut order if time runs short:** (1) FR7 prescription and FR8 follow-up, with FR2.3; (2) FR10.7 background updater, FR9.5 export, FR11.3 tour, FR5.5 zoom; (3) FR4.7 explore and FR6.2–FR6.5 editing; (4) FR3 urology stub. Each cut is recorded in the delivery plan and nothing that remains may refer to a cut screen.

## Functional Requirements

### FR1 — Clinical knowledge model (IB-01; C-T4)

- **FR1.1** One general graph model stores node types: symptom, metric, diagnosis, sub-type, test, treatment tier, drug, monitoring measure, response criterion, diet, watch-out, escalation trigger, interaction, and allergy cross-reactivity. It is not specific to any specialty.
- **FR1.2** Every node carries: a stable node ID, a type, a short label, content, at least one source citation (title, year, section or page), the knowledge-pack version that introduced or last changed it, and comments.
- **FR1.3** Edges carry a relationship type (for example "suggests", "confirmed by", "refines to", "first line", "escalate to", "monitor with") and the condition for following them (for example a lab threshold or severity grade).
- **FR1.4** Metric nodes store reference ranges per sex where the source gives them, plus any age or pregnancy band the source keys on (wireframes.md, Results and thresholds).
- **FR1.5** Knowledge is grouped into packs (for example "IBD", "Urology stub"). Each pack has its own version number, and every pack and version is shown wherever an answer appears.
- **FR1.6** Safety data (R-04): each drug node stores its drug class and cited contraindications (including pregnancy). Interaction nodes store a drug or class pair, a severity and a citation. Allergy cross-reactivity nodes map an allergen class to the drug classes it conflicts with, with a citation. For the demo case, the pack holds at least the penicillin allergy class, methylprednisolone, hydrocortisone, infliximab, ustekinumab, mesalamine and levothyroxine.
- **FR1.7** Version pinning (R-05):
  - A case is pinned to the pack version used when its walk started. A walk in progress always finishes on that version.
  - Reopening a case shows its pinned version. If a newer version is live, a banner says "Newer version vX.Y available: re-walk?", and a re-walk records both versions.
  - A follow-up verdict uses the current live version's response criteria and records both the case's version and the live version in the audit.
  - Replay always uses the session's recorded version.
- Acceptance: Given a node missing a source citation, When the pack is loaded, Then loading fails and names the node.
- Acceptance: Given a case walked on v1.3 and v1.4 published since, When the case is reopened, Then it still shows v1.3 with the re-walk banner, and When a follow-up is recorded, Then its audit entry lists v1.3 and v1.4.

### FR2 — IBD knowledge content (IB-02, IB-08; C-R4)

- **FR2.1** Ulcerative colitis branch: from findings to working diagnosis, confirming tests (stool culture, colonoscopy with biopsy, extent, severity), sub-type (extent and severity), treatment tiers 1–3 with entry criteria, monitoring, diet, watch-outs and surgery triggers.
- **FR2.2** Crohn's disease branch at the same depth as ulcerative colitis (rough-mockups Q7).
- **FR2.3** Each treatment tier has cited response-criteria nodes (the threshold for responding, partial response or not responding) used by follow-up visits (wireframes.md, fix R-02).
- **FR2.4** Every dose, frequency and duration comes from a cited source. Drug options within a tier (for example infliximab, ustekinumab) each carry their own fit criteria.
- **FR2.5** All guideline content is paraphrased and cited, never copied verbatim (discovered-rules.md).
- **FR2.6** The initial IBD pack is drafted with Claude while building and loaded directly by the builder as version v1.0. It is not run through the proposal flow (Q1).
- **FR2.7** An infectious-colitis alternative branch exists as a considered-but-not-taken node, so the explore flow (FR4.7) has something to open.

### FR3 — Second-specialty stub (IB-11; C-T4)

- **FR3.1** A urology pack with a handful of nodes is loaded through the same model as IBD, with no specialty-specific code.
- **FR3.2** A demo urologist profile can run one walk through the stub end to end.

### FR4 — Grounded agent (IB-03; C-T1, C-T3)

- **FR4.1** From free text, the agent extracts findings as structured chips (kind, name, value, unit, duration). It posts them as an editable "Confirm findings" form in the chat before walking.
- **FR4.2** The agent walks only by searching and traversing the graph. Each answer line is produced from one or more walked nodes and carries their node IDs.
- **FR4.3** A line with no backing node is never shown. The answer summary shows counts: steps, cited lines and ungrounded lines (the last must be 0).
- **FR4.4** When the graph needs a test result to refine further, the agent posts a "Needs more data" form naming the tests. On submit, it continues the walk.
- **FR4.5** When no node matches the findings, or the branch is not in any pack, the agent says "No grounded answer", shows ⊘ on the map and offers "Suggest adding this branch". It never guesses.
- **FR4.6** The answer is a pathway in fixed order: findings → working diagnosis (with why) → confirm and refine → refined sub-type → treatment tiers with entry point marked → monitor → diet → watch-outs and surgery triggers.
- **FR4.7** Explore: from a map node or chat ("explore infectious colitis"), the agent shows that branch's tests and treatment in a separate lane without changing the main plan. It offers "Add these tests to the plan" and "Stop exploring".
- **FR4.8** Free text that changes the case (for example a new symptom) is added to the case history, and the agent offers "Review findings and re-walk".
- **FR4.9** Patient details (sex, weight, comorbidities, allergies) can be changed through a chat form or plain chat ("she's 62 kg"). The change updates reference ranges and weight-based doses at once, and the chat confirms what changed.
- **FR4.10** Claim check (R-03): before display, every answer line is broken into structured claims (diagnosis, test, drug, dose and unit, frequency, duration, threshold, tier). Each claim must match a field of a cited node exactly, after unit normalisation. A line with any claim that does not match is not shown. It is logged as rejected, and the ungrounded count in the summary includes it. The same check applies to the plain-language "why" (FR9.3).
- **FR4.11** Input handling (R-07):
  - **Convertible unit** (for example Hb in g/L): converted in one place and shown with the original value.
  - **Non-convertible unit or a non-numeric value:** the chip is marked invalid and the doctor is asked to fix it before the walk.
  - **Two different values for one metric:** the agent asks which one to use.
  - **Value outside the plausible range stored on the metric node:** the agent asks the doctor to confirm.
  - **Partly filled "Needs more data" form:** empty tests stay "? not yet tested", and the walk goes as far as the entered results allow.
  - **Free text sent during a walk:** queued and shown, and once the walk ends the agent offers "Review findings and re-walk".
- Acceptance: Given a model output line "Methylprednisolone 120 mg" citing N12, where N12's dose is 60 mg, When the claim check runs, Then the line is not shown and the ungrounded count is 1.
- Acceptance: Given "Hb 102 g/L", When findings are confirmed, Then the chip reads "Hb 10.2 g/dL (entered 102 g/L)".
- Acceptance: Given the demo patient (34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g) and results for stool culture (negative), colonoscopy (UC pattern), extent E3 and severity severe, When the walk completes, Then the pathway reaches "ulcerative colitis, pancolitis, severe", enters at Tier 2, and shows 0 ungrounded lines.
- Acceptance: Given findings that match no pack, When the walk runs, Then the answer is "No grounded answer" and no diagnosis or treatment line appears.

### FR5 — Consultation workspace (IB-06, IB-07; wireframes S3)

- **FR5.1** Split view: chat on the left, network map of the graph region used on the right. A sticky patient card sits above both and is never scrolled away.
- **FR5.2** Network map with fixed columns: Findings → Diagnosis → Tests → Sub-type → Treatment → Monitor/watch. Edge styles: walked, bypassed, not taken, exploring. Node badges: done ✓, test needed ?, not in pack ⊘, entry tier ▶.
- **FR5.3** Selection sync: selecting a chat line selects its node and opens the detail panel; selecting a node highlights its chat line.
- **FR5.4** During the walk, nodes and edges light up in walk order.
- **FR5.5** Zoom from 40% to 200% in 20% steps, plus Fit and 100%. The map scrolls in both directions when zoomed.
- **FR5.6** The workspace supports every state: empty, confirm findings, working, needs more data, answered, exploring, edit treatment, out of knowledge, and error.
- **FR5.7** Results show against reference ranges with colour, symbol and word: ↓ Low, ↑ High, ! Abnormal, ✓ Normal, ? Not yet tested, ◷ Planned.
- **FR5.8** Every agent form, once submitted, shrinks to a one-line summary. The doctor's answer appears as their own message, and map actions also post a line into the chat, so the thread is the case record.
- **FR5.9** Error state: a plain message and Retry, with every input kept (FR4 continues from where it failed).

### FR6 — Treatment detail and editing (wireframes S4)

- **FR6.1** The node panel shows type, drug, route, dose, frequency, duration or review point, pre-start checks, safety checks against the patient card, source, version and comments.
- **FR6.2** mg/kg doses are computed from the card's weight and shown with the formula.
- **FR6.3** An edit, started from the panel or from chat ("change dose to 40 mg"), opens an Edit treatment form in the chat prefilled with current values. Changing the drug resets route, dose and frequency to that drug's sourced suggestion.
- **FR6.4** On apply, the allergy and weight checks run again. Edited fields are marked "✎ edited", and the panel reads "Edited by <profile>".
- **FR6.5** The original suggestion, the edit and the editor are written to the session audit.

### FR7 — Prescription (wireframes S5, fix R-01)

- **FR7.1** The draft is generated from the answered plan, including edits, plus the patient's current medication from the card. Each line shows its source chip (node ID, "Card", or "Manual").
- **FR7.2** Generic international format: generic drug names, form and route, dose, frequency, duration and patient instructions. There are no country-specific fields (Q7).
- **FR7.3** Safety checks use only the safety nodes from FR1.6. They block signing on an allergy conflict, a pregnancy contraindication, or any line still holding a placeholder value. When a drug or a recorded allergy has no safety node, the check shows "? Not checked: no grounded safety data" and never "no conflict". Signing then requires the doctor to tick that they checked it themselves, and that tick is audited (R-04).
- **FR7.4** Flagged interactions and duplicate drug classes warn. Signing then requires ticking that they were reviewed, which is recorded in the audit.
- **FR7.5** Field sources: doctor details from the demo profile (marked "demo"), patient details from the card (marked "synthetic"), diagnosis from the sub-type node, ℞ lines from treatment nodes or logged edits, and advice, warnings and follow-up from the monitor, diet and watch-out nodes.
- **FR7.6** Signing requires the responsibility checkbox. It stamps the time, prescription ID and knowledge version, saves the PDF to the case audit, and offers Download and Print. Every PDF carries "DEMO · SYNTHETIC PATIENT".
- **FR7.7** Void and re-issue: asks for a reason, marks the original VOID (never deleted) and opens a prefilled draft that goes through the same checks.
- **FR7.8** If PDF generation fails, a plain message and Retry appear, and the signed record is not marked complete until the PDF exists.

### FR8 — Follow-up visit (wireframes S6, fix R-02)

- **FR8.1** A follow-up opens the same patient with the current treatment and a visit chip. The agent names the response measures and their nodes and posts a results form.
- **FR8.2** Trend charts show one line per measure across visits, a labelled target or reference band with its node chip, and a status tag in words.
- **FR8.3** The verdict (✓ Responding, ◐ Partial, ✕ Not responding) is computed only from cited response-criteria nodes (FR2.3), with numbered reasons and node chips. It leads to continue, taper or escalate, with the matching prescription action (FR7).
- **FR8.4** For a measure with no response-criterion node, the screen shows the trend but no verdict: "No grounded response criterion for this measure", with ⊘ and "Suggest adding it".
- **FR8.5** Each follow-up is saved to the audit as a new visit.

### FR9 — Session audit and explanation (IB-04; C-R3)

- **FR9.1** Every session records the signed-in profile, the pack and version, the inputs (verbatim text and confirmed chips), the path walked (node IDs in order), the answer as given, the sources with the version at that time, and every edit, explore, override, prescription and visit.
- **FR9.2** Audit records are append-only. Corrections are new entries; nothing is edited or deleted.
- **FR9.3** A plain-language "why" is written by the model only from the walked nodes and their sources. Every sentence carries node chips, and a sentence with no node is removed before display (Q8).
- **FR9.4** History lists sessions with search by finding, diagnosis or session ID, and filters by outcome (answered, needs data, out of knowledge). An empty history shows "No sessions yet".
- **FR9.5** "Replay on canvas" reopens the session's map with its walked path, read-only. "Export" downloads the session record as a JSON file and a readable PDF.
- **FR9.6** Explored branches are marked "explored, not acted on" unless tests were added.

### FR10 — Knowledge updates and versions (IB-10, IB-12; Q1–Q3)

- **FR10.1** A doctor can suggest a change to a node, with a source (URL or uploaded document), section or page, what should change, and a comment.
- **FR10.2** Linking a new source makes the agent draft the node changes it implies, through the configured model.
- **FR10.3** Every doctor-suggested or model-drafted change becomes a proposed version (vX.Y → vX.Y+1 draft) with a before and after view, and is never live until published (Q1).
- **FR10.4** A seeded "clinical reviewer" profile publishes or rejects a proposal from the Knowledge screen, with a comment. There is no full reviewer queue (Q2).
- **FR10.5** On publish, the pack version goes up. New sessions use the new version; past sessions keep the version they used.
- **FR10.6** Version history lists version, status (Live, Superseded, Proposed, Rejected), date, author, change and comment.
- **FR10.7** The background updater runs on a schedule (default daily, configurable). It re-checks each linked source and, when one has changed, drafts a proposed version for review. A source that can't be reached is logged and skipped, and the rest continue (Q3).
- **FR10.8** If a proposal submission fails, a plain message appears and the form keeps its input.
- **FR10.9** Untrusted sources (R-08):
  - Uploaded documents and fetched pages are treated as data, never as instructions to the drafter.
  - Fetching allows http(s) only. Local and private network addresses are refused, and fetches are capped at 10 MB and 20 seconds.
  - Drafted node text that repeats more than 25 consecutive words of the source is flagged "possible verbatim copy" and cannot be published until it is rewritten.
  - The before-and-after view shows the source passage each drafted change came from.

### FR11 — Sign-in and first run (wireframes S1, S1a; Q4)

- **FR11.1** Sign-in is picking a seeded demo profile: Dr. Maya (gastroenterologist), demo urologist, demo clinical reviewer. There is no password.
- **FR11.2** On a profile's first sign-in, a disclaimer with two required checkboxes (responsibility; synthetic patients only) is shown. Acceptance is logged once with date and pack version, and is asked again when the disclaimer or a pack changes materially.
- **FR11.3** A three-step tour (talk to Brahma, read the map, check, edit and sign) follows; it can be skipped and replayed.

### FR12 — Patients (wireframes S2)

- **FR12.1** The landing page searches patients by case ID, finding or diagnosis and lists recent patients with a status chip (follow-up due, needs data, out of knowledge, plan in place).
- **FR12.2** "Create new patient" opens an empty case with a generated case ID labelled "synthetic". A case is left with "Exit case".
- **FR12.3** Reopening a case restores its chat thread, map, patient card and any unsubmitted form values.
- **FR12.4** A search with no results says so and offers "Create new patient".

### FR13 — Benchmark (IB-09; C-Q2; Q6)

- **FR13.1** 20 synthetic cases: 8 ulcerative colitis, 8 Crohn's disease, 4 urology stub. Each case has inputs and the expected pathway.
- **FR13.2** A **recommendation** is one line of the answer that names a working diagnosis, a test, a sub-type, a treatment (drug, dose or tier), a monitoring threshold, or an escalation trigger. Diet and watch-out lines also count (R-02).
- **FR13.3** Each case runs twice, on the same model and with the same prompt asking for a cited pathway: (a) the agent with the graph; (b) the model with no graph, given the pack's source list (titles only) and asked to cite a source for each recommendation.
- **FR13.4** Grounding is checked automatically, not by hand. A recommendation is grounded when it cites a source in the pack AND a node from that source supports every claim in it, using the same claim check as FR4.10. For run (b), the check looks for a supporting node under the cited source. So the plain model scores 0% only if it is actually unsupported, not by construction (R-02).
- **FR13.5** Two results are reported for each run: the grounded share, and agreement with the expected pathway (recommendations that match an expected line ÷ expected lines).
- **FR13.6** The pass mark has two parts, over the 16 IBD cases: (1) the graph run has at least 95% grounded recommendations, and (2) the graph run's grounded share and agreement are each higher than the plain run's. The 4 urology cases are shown but do not count toward the pass.
- **FR13.7** You write the expected pathways with Claude from the pack. Your family or friend reviewer checks the 16 IBD pathways before the final benchmark run. The check is recorded as "Reviewed by <name>, <date>" per case (revision decision).
- **FR13.8** The benchmark runner throttles to the provider's rate limit, saves each case result as it finishes, and can resume a stopped run without repeating finished cases (R-06).
- **FR13.9** The benchmark page shows:
  - totals
  - the graph-vs-plain grounded share and agreement
  - per-case results, filterable by All, UC, Crohn's and Urology
  - Pass or "Below 95%" as words
- **FR13.10** The benchmark run used for submission runs on a Meta model through the Meta Model API (discovered-rules.md). The page shows which model and date produced it. If Meta Model API credentials are not working by **Nov 2, 2026, 9:00 PM ET**, you choose the fallback for the submitted demo and benchmark on that date, and this requirement and C-T1 are updated with that choice before the video is recorded (revision decision, R-06).

### FR14 — Model provider configuration (team-practices.md, Way of Working)

- **FR14.1** The model provider is chosen by configuration only: Meta Model API, Claude, or a free hosted Llama tier (for example Groq or OpenRouter). Switching needs no code change.
- **FR14.2** The free hosted Llama option is the first provider set up (practices Q10).
- **FR14.3** The current provider and model name are shown in the app footer and written to every session audit.
- **FR14.4** A provider error (timeout, rate limit, bad key) appears as the workspace error state (FR5.9) and is logged with the provider name. Nothing is silently retried more than twice.

### FR15 — Disclaimers and data rules (C-R1, C-R2)

- **FR15.1** "Decision support, not diagnosis" and the pack version show on every screen and every answer.
- **FR15.2** Every patient name and ID in the app and its seed data is invented and labelled "synthetic".

### FR16 — Repository and local setup (team-practices.md, Deployment)

- **FR16.1** The public repo has a README covering prerequisites, install, configuration, run, test and benchmark steps.
- **FR16.2** An `.env.example` lists every required environment variable with no real values.
- **FR16.3** The commit the demo video is recorded from is tagged.

## Non-Functional Requirements

- **NFR1 — Response time:** progress appears in the chat within 3 seconds of submitting, and keeps updating while the agent walks. The full cited pathway for the demo case arrives within 60 seconds, measured on the model used for the submitted demo (the Meta Model API model, or the Nov 2 fallback under FR13.10). Times on the free hosted Llama tier are logged for information but are not pass/fail (Q5; R-09).
- **NFR2 — Groundedness:** 0 ungrounded lines in the demo case (C-Q1) and at least 95% grounded recommendations across the 16 IBD benchmark cases (C-Q2), both measured with the claim check (FR4.10, FR13.4).
- **NFR3 — Accessibility (WCAG 2.1 AA), checked against these five items:**
  1. Status is never shown by colour alone (symbol plus word).
  2. Text contrast is at least 4.5:1, including small labels and result chips.
  3. Interactive targets are at least 44 × 44 px. Map nodes (100 × 72 px) meet this, so there is no exemption.
  4. Everything is keyboard operable, including map zoom, node selection and the card toggle, with visible focus.
  5. Inputs are labelled, and map nodes have `aria-label`s with type, status and result.

  (rough-mockups Q6; R-09)
- **NFR4 — Platform:** runs on a desktop or laptop browser (latest Chrome, Firefox, Safari) at widths of 1280 px and up. Tablet and phone are out of scope.
- **NFR5 — Secrets:** API keys live only in environment variables. The repo and its history hold none, and CI needs no keys because model calls are stubbed (discovered-rules.md; team-practices.md, Testing Posture).
- **NFR6 — Data:** only synthetic data is stored or shown. The app has no import path for real patient records (C-R1).
- **NFR7 — Auditability:** audit records are append-only (FR9.2), and each records the provider, model, pack version and profile. An audit record can be exported (FR9.5) (C-R3).
  - **How append-only is enforced:** the storage layer has no update or delete operation for audit records, and the database rejects UPDATE and DELETE on audit tables (for example with triggers). A test proves both.
  - **Crash mid-write:** every audit write is one transaction, so a crash leaves the last committed entry intact and no partial entry.
  - **Same case in a second tab:** the second tab opens read-only with the notice "This case is open in another tab" (R-10).
- **NFR8 — Reliability:** every integration boundary (model provider, source fetch, PDF generation, local storage) surfaces errors to the user or the log, and never fails silently. A failed walk keeps every input (construction guardrails).
- **NFR9 — Testability:** test-after, with 80% line coverage measured separately for backend and frontend. CI runs lint, tests and coverage on every push to `main`. A browser smoke test of the demo walk runs against the local app (team-practices.md, Testing Posture).
- **NFR10 — Setup:** a fresh clone runs locally with the README steps and one provider key in under 15 minutes on macOS.
- **NFR11 — Observability:** each walk logs its node path, model calls (provider, latency, token counts where available) and errors to a local log file, so a failed demo run can be diagnosed.
- **NFR12 — Maintainability:** Ruff for Python; ESLint, Prettier and TypeScript strict for the frontend. CI fails on any lint error (team-practices.md, Code Style).

## Constraints

| ID | Constraint | Source |
|----|------------|--------|
| C-T1 | The submitted demo and the benchmark run on a Meta model through the Meta Model API; Claude only for building and drafting content. If credentials aren't working by Nov 2, 2026, 9:00 PM ET, the fallback is chosen then (FR13.10) | constraint-register.md; discovered-rules.md; R-06 |
| C-T2 | Python backend and agent; TypeScript/React frontend | constraint-register.md |
| C-T3 | Answers only from the knowledge graph, citing nodes and sources | constraint-register.md |
| C-T4 | The knowledge model generalises to other specialties | constraint-register.md |
| C-O1 | Submit before Nov 4, 2026, 9:00 PM ET | constraint-register.md |
| C-O2, C-O3 | One builder; evenings plus Oct 31 – Nov 1 weekend hours | constraint-register.md |
| C-R1 – C-R4 | Synthetic data only; decision support, not diagnosis; no HIPAA or certification claim; guideline content paraphrased and cited | constraint-register.md |
| Delivery | Public GitHub repo plus demo video, run locally; no hosted URL (replaces C-T5) | team-practices.md |
| Way of working | Commit straight to `main`; no thin slice first | team-practices.md |

## Assumptions

- [assumption] Local storage (for example SQLite plus files) is enough for one doctor running locally; no multi-user concurrency is needed, because it runs on one machine.
- [assumption] English only, because the demo audience and sources are English.
- [assumption] Meta Model API credentials arrive before the demo video and benchmark run; until then the free hosted Llama tier and Claude stand in (practices Q7, Q10).
- [assumption] The family or friend reviewer checks the IBD pathway content before submission (intent-capture Q10). Their window is not yet known.
- [assumption] The hackathon accepts knowledge content drafted with Claude as long as the running product uses a Meta model. This is unconfirmed.
- [assumption] Times are shown in the machine's local time zone; audit timestamps are stored in UTC.

## Out of Scope

- Real patient data, EHR integration, and any import of real records (C-R1)
- A hosted URL, staging or production environment (team-practices.md)
- Full content for specialties other than IBD beyond the urology stub
- A full knowledge reviewer queue, notifications, settings and profile, close-case summary, specialty switcher UI beyond showing the pack (wireframes handover, end-to-end coverage)
- Real sign-in, passwords, SSO, and medical registration checks (Q4)
- Country-specific prescription rules (Q7)
- Tablet and phone layouts; pinch zoom and drag to pan
- HIPAA scope or any certification (C-R3)

## Open Questions

Every question is owned by you, the builder (R-11).

| Question | Decide by | What changes under each answer |
|----------|-----------|--------------------------------|
| Do Meta Model API credentials work? | Nov 2, 2026, 9:00 PM ET | Yes: FR13.10 runs as written. No: you choose the fallback and C-T1 and FR13.10 are updated before the video. |
| Do the free Llama tier's rate limits allow the 40 benchmark runs (20 cases × 2)? | First full benchmark run, by Nov 1 | Yes: no change. No: FR13.8 resume and throttling spread the run, or development runs use a subset of cases. |
| Does the hackathon accept knowledge content drafted with Claude? | Oct 30, 2026 (check the rules or ask the organisers) | Yes: FR2.6 stands. No: the pack is redrafted through the Meta or Llama provider using FR10.2, before the benchmark. |
| Can your family or friend reviewer check the IBD content and the 16 expected pathways in time? | Oct 31, 2026 | Yes: FR13.7 stands. No: the pathways are marked "not clinically reviewed" on the benchmark page and in the video. |
| Should an edited treatment need a second sign-off before it counts as the plan? | Before User Stories | v1 assumes no. Yes: add a sign-off step to FR6.4. |
| Is a trademark and cultural check on "Brahma" needed before the repo goes public? | Before the repo is made public | Yes: run it; rename if it fails. No: no change. |
