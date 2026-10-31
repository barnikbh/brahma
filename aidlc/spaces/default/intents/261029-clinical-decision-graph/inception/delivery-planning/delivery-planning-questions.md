# Delivery Planning — Questions

Context: eight units with dependencies in `unit-of-work-dependency.md`; priorities and cut order in `requirements.md`; one builder, evenings plus Oct 31 – Nov 1 weekend hours, submission Nov 4, 2026, 9:00 PM ET; no thin slice first (`team-practices.md`). A **Bolt** is one build pass over a piece of the work that ends in something that runs. Per your project rule to keep process detail light and pick sensible defaults instead of asking (`project.md`, Corrections), each answer below is a default from those sources. The summary at the end is your one check.

## Q1. [Sequencing] What to build first

A. Risk first: the knowledge content and the grounded walk (U1, U2, U3, U4) first, because the core promise and the untested model access are the biggest unknowns; then the web app (U8); then knowledge updates (U5) and the benchmark (U7); prescriptions and follow-up (U6) last, only if time allows
B. Value first: the screens first against stubbed data, then the backend
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: requirements.md cut order; intent risk that model access and grounding are unproven)

## Q2. [Sequencing] Scoring model

A. No formal scoring; order by dependency and the approved cut order
B. Weighted scoring (value and urgency against size)
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: priorities are already set; scoring adds nothing for one builder)

## Q3. [Bolts] Bolt size

A. One unit per Bolt (8 Bolts)
B. Several units per Bolt
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: matches the units and the one-unit-at-a-time build already recorded)

## Q4. [Bolts] Parallel or one after another

A. One after another (one builder; the recorded build setting is one unit at a time)
B. Several in parallel
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: recorded Construction setting, serial)

## Q5. [Dependencies] Outside things that can hold us up

A. Meta Model API credentials (you, decide by Nov 2), the hackathon's rule on Claude-drafted content (you, by Oct 30), and your family or friend reviewer checking the IBD content and pathways (by Oct 31), each with the fallback already in the requirements
B. Something else as well
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: requirements.md, Open Questions)

## Q6. [Verification] The command that checks each finished unit

A. Defer: the project has no code yet, so the first unit checkpoint will ask for it
B. Pick a command now
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: greenfield; nothing runnable exists yet)

## Consolidated Summary Confirmation

- Risk first: U1 knowledge graph and content, U2 platform, U3 cases and safety, U4 grounded agent; then U8 web app; then U5 knowledge updates and U7 benchmark; U6 prescriptions and follow-up last, only if time allows (Q1)
- No formal scoring; the order follows the dependencies and the approved cut order (Q2)
- One unit per Bolt, built one after another (Q3, Q4)
- Outside dependencies: Meta credentials by Nov 2, the hackathon rule on Claude-drafted content by Oct 30, and the reviewer's check by Oct 31, each with its fallback from the requirements (Q5)
- The check command for finished units is chosen at the first unit checkpoint, since no code exists yet (Q6)

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
