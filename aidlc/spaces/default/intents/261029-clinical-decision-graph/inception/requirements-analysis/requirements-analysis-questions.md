# Requirements Analysis — Questions

Context: depth Standard. Most behaviour is already fixed by the approved intent (`intent-statement.md`), scope (`scope-document.md`), wireframes (`wireframes.md`, `user-flow.md`) and team practices (`team-practices.md`). These questions cover only what those leave open. Everything else I'll write as requirements or assumptions you can correct.

## Q1. [Knowledge] AI-generated knowledge content

The app can generate knowledge content through a model (team-practices.md, Way of Working), and a doctor can link a source for the agent to ingest. What happens to content a model drafts?

A. It always becomes a proposed version that a person must review and publish; it is never live until then
B. It goes live at once as a new version, marked "AI-drafted", and can be rolled back
C. Proposals go live after a person reviews them, except the initial pack, which the builder loads directly
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q2. [Knowledge] Who publishes a proposed version in the demo

The wireframe shows Proposed → Clinical review → Published, and the reviewer queue is out of v1. Who moves a proposal to Published in the demo?

A. A seeded "clinical reviewer" demo account publishes it from the Knowledge screen (a minimal review step, no full queue)
B. The proposing doctor can publish their own proposal after a confirmation
C. Proposals stay as proposals in v1; only the builder publishes, outside the app
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. [Knowledge] What the background updater does in v1

The silent background updater is a scheduled stub in v1 (scope-document.md). What should the stub do?

A. On a schedule, re-check each linked source for changes and, when one changed, draft a proposed version for review
B. Run on a schedule and only log that it ran (a placeholder for later)
C. Leave it out of the code entirely; describe it in the README only
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. [App] Sign-in for a local app

The app now runs locally only (team-practices.md, Deployment). The audit still names a doctor. How does a user sign in?

A. Pick a seeded demo profile (Dr. Maya, demo urologist, demo reviewer) with no password; each session is tied to that profile
B. Seeded demo accounts with passwords kept in the local environment file
C. No sign-in at all; every session is logged as one demo doctor
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. [Quality] How fast an answer must be

The agent walks the graph and calls a model at each step, and the free hosted tier may be slow or rate-limited. What is acceptable for the demo walk?

A. First progress shown within 2 seconds; the full cited pathway within 30 seconds
B. Full pathway within 60 seconds, progress shown all the way
C. No target; correctness matters more than speed for the demo
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q6. [Benchmark] The 20-case mix

The review left the benchmark case mix open (wireframes.md, finding R-03). How should the 20 synthetic cases split?

A. 8 ulcerative colitis, 8 Crohn's disease, 4 urology stub; all 20 count toward the 95% pass
B. 8 ulcerative colitis, 8 Crohn's disease, 4 urology stub; only the 16 IBD cases count toward the pass
C. 10 ulcerative colitis, 10 Crohn's disease; urology is shown in the demo only, not benchmarked
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q7. [App] Prescription format

The prescription screen follows Indian conventions in the handover (generic names in capitals, registration number, NMC guidance). Which format does v1 follow?

A. Indian (NMC) format, as in the handover
B. A generic international format with no country-specific rules
C. Indian format, clearly labelled "demo format, not validated against NMC rules"
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q8. [Audit] The plain-language "why"

Each audited session has a plain-language explanation of why the answer was reached. How is it written?

A. The model writes it only from the walked nodes and their sources; every sentence carries node chips, like the answer
B. It is assembled from fixed templates over the walked path, with no model writing
C. The model writes it freely as a summary, marked as a model summary
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

- Knowledge content a model drafts, or a linked source the agent ingests, becomes a proposed version that a person reviews before it goes live; only the initial knowledge pack, drafted with Claude while building, is loaded directly by you (Q1)
- A seeded "clinical reviewer" demo profile publishes proposed versions from the Knowledge screen; there is no full reviewer queue (Q2)
- The background updater runs on a schedule, re-checks each linked source and, when one has changed, drafts a proposed version for review (Q3)
- Sign-in is picking a seeded demo profile (Dr. Maya, demo urologist, demo reviewer) with no password; every session and audit record names that profile (Q4)
- Speed: progress shows throughout the walk, and the full cited pathway arrives within 60 seconds (Q5)
- Benchmark: 20 synthetic cases, 8 ulcerative colitis, 8 Crohn's disease and 4 urology stub; only the 16 IBD cases count toward the 95% grounded pass (Q6)
- Prescriptions use a generic international format with no country-specific rules (Q7)
- Each session's plain-language "why" is written by the model only from the walked nodes and their sources, with node chips on every sentence, like the answer (Q8)
- Carried in from earlier stages: the deliverable is the public repo plus demo video, run locally (no hosted URL), and the Oct 31 deployed-slice milestone is dropped (team-practices.md); the requirements will record these as superseding the scope document

Does this all look correct before I generate the requirements artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
