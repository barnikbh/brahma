# Bolt Plan — Brahma

A **Bolt** is one build pass over one unit of work that ends in something that runs and passes its tests. There is one unit per Bolt, built one after another (Q3, Q4). There is no walking skeleton, meaning no thin end-to-end slice built first (`team-practices.md`).

Upstream: `unit-of-work.md` and `unit-of-work-dependency.md` (U1–U8 and their dependencies), `unit-of-work-story-map.md`, `requirements.md` (priority and cut order, open questions), `stories.md`, `mockups.md`, `components.md`, `contract-summary.md`, `team-practices.md`. Answers: `delivery-planning-questions.md` Q1–Q6.

**Order rule:** risk first (Q1). Bolts follow the dependency map, because the build runs units in that order.

## Order Note

You confirmed "web app (U8) right after the grounded agent, then knowledge updates (U5) and benchmark (U7)". The approved dependency map has U8 depending on U5 and U7, so the build runs U5 and U7 **before** U8. The plan below follows the build order. To get the web app straight after U4, U8's link to U5 and U7 would have to become optional, as U6's already is. That change belongs in Units Generation, and you can choose it at this gate.

## Bolts

| Bolt | Unit | Target window | Priority |
|---|---|---|---|
| B1 | U1 u1-knowledge-graph | Oct 29 – 30 (UC content); Crohn's content added by Nov 1 | Must |
| B2 | U2 u2-platform | Oct 30 | Must |
| B3 | U3 u3-cases-safety | Oct 31 | Must |
| B4 | U4 u4-grounded-agent | Oct 31 – Nov 1 | Must |
| B5 | U5 u5-knowledge-updates | Nov 1 | Must (drafting Should, scheduler Could) |
| B6 | U7 u7-benchmark | Nov 1 – 2 | Must |
| B7 | U8 u8-web-app | Nov 1 – 2 (built against stubbed API from B4 onward) | Must |
| B8 | U6 u6-prescriptions-followup | Nov 2, only if time allows | Could, cut first |
| — | Demo video and submission | Nov 3 – 4, before 9:00 PM ET | Must |

### B1 — Knowledge graph and content (U1)

- **Done when:** the IBD pack v1.0 loads with UC and Crohn's branches, the infectious-colitis alternative, safety nodes for the demo drugs and response criteria; a node with no source fails the load and names the node; the urology stub loads through the same model; unit tests pass.
- **Confidence hypothesis:** the general knowledge model can hold a real clinical pathway at full depth, and the content can be authored in the time available.
- **Expected demo:** load the pack and print the UC path from findings to Tier 2 with sources.

### B2 — Platform (U2)

- **Done when:** audit writes are append-only (an update or delete fails, and a test proves it); three demo profiles plus the benchmark runner exist; disclaimer acceptance is stored; the model gateway calls the free Llama tier and Claude by configuration, throttles, retries at most twice and logs every call; tests use recorded responses.
- **Confidence hypothesis:** switching model provider is configuration only, and the free tier is usable.
- **Expected demo:** the same prompt answered by two providers, switched by an environment variable.

### B3 — Cases and safety (U3)

- **Done when:**
  - Cases and patients are created and searched, and reopen with their thread.
  - Findings validate: unit conversion, conflicts, plausible range.
  - Version pin and the tab lock with heartbeat work.
  - Weight-based dose is computed, and safety checks return "Not checked" when there's no node.
  - All acceptance criteria for US2.1, US4.1 and US4.2 pass at the unit level.
- **Confidence hypothesis:** safety checks can stay grounded with no gaps filled from model memory.
- **Expected demo:** the demo patient's infliximab dose at 58 kg, and a penicillin-class conflict.

### B4 — Grounded agent (U4)

- **Done when:**
  - The demo walk (AC3.2.1) reaches UC pancolitis severe at Tier 2 with 0 ungrounded lines.
  - The deliberately wrong citation is held back (AC3.2.3).
  - The walk handles needs more data, out of knowledge, explore and re-walk.
  - The SSE stream sends only checked lines, with first progress within 3 s.
  - The "why" sentences all carry node chips.
  - The session is recorded in the audit.
- **Confidence hypothesis:** an agent constrained to search and traverse the graph can answer the demo case with zero ungrounded lines. This is the core promise.
- **Expected demo:** the demo walk streamed in a terminal client, with counts.

### B5 — Knowledge updates (U5)

- **Done when:**
  - A suggestion becomes a proposed version.
  - The reviewer publishes it, and the version goes up while past sessions keep theirs.
  - Fetch limits and the verbatim-copy flag work.
  - If time allows: drafting from a source (Should), then the scheduled check (Could).
- **Confidence hypothesis:** the update loop keeps humans in control of every change.
- **Expected demo:** suggest a change to N13, publish as the reviewer, and see v1.4 in the version history.

### B6 — Benchmark (U7)

- **Done when:**
  - 20 cases with expected pathways exist; the 16 IBD ones are marked for the reviewer's check.
  - Graph and plain runs are scored by the same claim check.
  - The two-part pass is computed over the IBD cases.
  - A stopped run resumes.
  - The results page data is available.
- **Confidence hypothesis:** the graph-grounded agent clearly beats the same model with no graph on grounding and agreement.
- **Expected demo:** a full run on the free tier with the pass card.

### B7 — Web app (U8)

- **Done when:**
  - Every Must screen from the handover is built with the A1–A8 annotations: sign-in, first run, Patients, the workspace in all states, node panel, History, Knowledge and Benchmark.
  - Chat and map stay in sync.
  - The five accessibility items pass.
  - The browser smoke test of the demo walk passes against the local app.
  - Prescription and follow-up screens appear only when U6 is mounted.
- **Confidence hypothesis:** a doctor can follow and verify the walk at a glance, which is the demo video's main shot.
- **Expected demo:** the full demo walk in the browser, as it will appear in the video.

### B8 — Prescriptions and follow-up (U6, Could)

- **Done when:** a prescription is drafted, checked, signed into a PDF and can be voided; a follow-up visit gives a grounded verdict, or none when there is no criterion node.
- **Confidence hypothesis:** the grounded plan carries through to everyday clinical actions.
- **Expected demo:** sign the Tier 2 prescription; record a day-14 visit.
- **Cut rule:** if B7 isn't done by Nov 2 noon, B8 is cut. Nothing else changes (ADR-001).

## Submission (Nov 3 – 4)

- If Meta credentials work, re-run the benchmark and the demo walk on the Meta model. If not, apply the fallback chosen on Nov 2 (FR13.10).
- Record the video on a tagged commit. Submit the repo and the video before Nov 4, 9:00 PM ET.

## Backlog (not scheduled)

- **Personal versions of the knowledge graph (low priority, added Oct 31, no screen planned yet).**
  - A doctor's knowledge update stays with that doctor, like a simple branch: Brahma starts from the global version, applies the doctor's update, and saves it as their own version.
  - A reviewer reviews it and publishes it, which makes it the global version for every doctor.
  - Builds on the Knowledge update conversation (browse, free text and source URLs, follow-up questions, "updated by who and when").
  - Today, a published change becomes global at once, and all doctors share one pack version.
  - Not needed for the demo or the submission.
- **Also cut for now (Oct 30):** prescriptions and follow-up visits (U6), the benchmark (U7).

## Construction Settings

- One unit at a time, each through its design stages and code generation, then a checkpoint (recorded: unit-major, serial, checkpoints on).
- The command that checks each finished unit is chosen at the first checkpoint (Q6).
