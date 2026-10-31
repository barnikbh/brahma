# Domain Design — Questions

Context: the approved `requirements.md`, `stories.md` and `team-practices.md` fix almost every boundary. Per your project rule to keep process detail light and pick sensible defaults instead of asking (`project.md`, Corrections), each answer below is the default I chose from those sources. The summary at the end is your one check.

## Q1. [Boundaries] How finely to split the system

A. Twelve building blocks along the requirement groups: knowledge graph, knowledge updates, model gateway, consult agent, grounding guard, cases, treatment and safety, prescriptions, follow-up, audit, identity, benchmark, plus the doctor web app
B. Five coarse blocks matching your original idea: knowledge, agent, audit, app, update layer
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: matches the requirement groups and the cut order, so prescriptions and follow-up can be dropped as whole blocks without touching the rest; option B mixes cut-first and must-have code in one block)

## Q2. [Boundaries] Where the claim check lives

A. Its own block (grounding guard), used by the consult agent, the "why" explanation, follow-up verdicts and the benchmark
B. Inside the consult agent
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: requirements FR4.10, FR9.3, FR13.4 all need the same check; one block means one test suite proves the core promise)

## Q3. [Entities] Who owns the case record and the audit

A. Cases owns patients, cases and the chat thread; Audit owns the append-only audit entries and session records; every other block writes to the audit only through Audit
B. Audit owns everything about a session, including the chat
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: the chat changes while a case is open, the audit never changes; NFR7 append-only is easiest to enforce in a block that has no update path)

## Q4. [Interaction] How blocks call each other

A. Direct in-process calls (one local app), with the walk streamed to the web app
B. Events through a message queue
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: runs locally for one doctor; a queue adds setup cost with no benefit; deployment shape is decided later in Units Generation)

## Consolidated Summary Confirmation

- Twelve building blocks plus the doctor web app, along the requirement groups, so prescriptions and follow-up can be cut as whole blocks (Q1)
- The claim check is its own block (grounding guard), shared by the answer, the "why", follow-up verdicts and the benchmark (Q2)
- Cases owns patients, cases and the chat; Audit owns the append-only audit, and every other block writes to it only through Audit (Q3)
- Blocks call each other directly inside one local app, with the walk streamed to the web app; how they are packaged is decided in the next stage (Q4)

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
