# Risk and Sequencing Rationale — Brahma

A **Bolt** is one build pass over one unit of work that ends in something that runs.

Upstream: `bolt-plan.md`, `unit-of-work-dependency.md`, `requirements.md` (priority, cut order, open questions), `components.md`, `contract-summary.md`, `stories.md`, `mockups.md`, `team-practices.md`. Answers: `delivery-planning-questions.md` Q1–Q6.

## Heuristic

**Risk first** (Cohn's risk-value ordering, restricted to the high-risk end), within the dependency map. No weighted scoring such as WSJF (value and urgency divided by size) is used: priorities are already fixed by the approved cut order, and scoring adds nothing for one builder (Q2).

## Why This Order

| Rank | Risk retired | Bolt |
|---|---|---|
| 1 | Can the clinical pathway be authored at full depth, cited and paraphrased, in time? The content is the largest single item (unit-of-work.md, U1 note) | B1 |
| 2 | Does the model provider swap actually work, and is the free tier usable while Meta access is pending? | B2 |
| 3 | Can safety and dose checks stay grounded with no gaps filled from model memory? | B3 |
| 4 | **The core promise:** can the walk answer with zero ungrounded lines, including computed doses? | B4 |
| 5 | Does the update loop keep publishing human-controlled? | B5 |
| 6 | Does the benchmark prove the promise against a plain model? (judges' proof) | B6 |
| 7 | Can the doctor follow it at a glance? (the video) | B7 |
| 8 | Nice-to-have clinical actions | B8 (cut first) |

## Deviations From Your Stated Order

You confirmed U8 before U5 and U7. The dependency map makes U8 depend on U5 and U7, so the build runs B5 and B6 before B7. This is not a scoring choice, it is how the map is drawn. U8's screens can still be built against stubbed API responses from B4 onward, so screen work isn't blocked. The way to restore your order is to make U8's links to U5 and U7 optional, as U6's already is (a Units Generation change).

## Schedule Risk

- Capacity is evenings plus the Oct 31 – Nov 1 weekend. B4 and B7 are both rated XL, and both land on the weekend and Nov 2.
- Everything after B4 is compressed into Nov 1–2. B8 has an explicit cut rule (Nov 2 noon), and the requirements' cut order covers anything beyond it: (2) updater, export, tour and zoom; (3) explore and editing; (4) urology stub.
- Nov 3 is kept for re-running the benchmark and demo on the Meta model or the fallback (requirements review R-13, accepted as risk; planned here anyway).

## What Worries Us Most

1. Meta access arriving late: covered by the gateway (B2) and the Nov 2 decision.
2. Content volume for full-depth UC and Crohn's: covered by B1 going first, with Crohn's allowed to finish by Nov 1.
3. The grounded walk being slower than 60 s on the free tier: measured in B4; it is pass/fail only on the submission model (NFR1).
