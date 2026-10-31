# Units Generation — Questions

Context: the approved `components.md` (12 blocks plus the web app) and `decisions.md` (ADR-001 – ADR-005) set the boundaries; `team-practices.md` says no thin slice first (walking skeleton off) and one builder committing to `main`. Per your project rule to keep process detail light and pick sensible defaults instead of asking (`project.md`, Corrections), each answer below is a default from those sources. The summary at the end is your one check.

## Q1. [Units] Unit boundary strategy

A. By feature area, grouping blocks that change together: knowledge graph and packs; platform (audit, identity, model gateway); cases and safety; grounded agent; knowledge updates; prescriptions and follow-up; benchmark; web app (8 units)
B. One unit per block (13 units)
C. Two units: backend and frontend
D. Not yet defined
X. Other (please specify)

[Answer]: A (default: keeps the cut-first prescriptions and follow-up as one removable unit (ADR-001) while keeping the unit count manageable for one builder; B is too many hand-offs; C hides the cut line)

## Q2. [Units] Deployment model

A. One local backend process serving every backend unit's API, plus the React web app; units are libraries or modules inside it
B. Each unit as its own service
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: ADR-005, local only, one doctor)

## Q3. [Units] Parallel work

A. Allow units with no dependency between them to be built side by side
B. Strictly one unit at a time in dependency order
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: the DAG records it; whether to actually run anything in parallel is a Delivery Planning choice)

## Q4. [Units] Integration between units

A. Direct in-process calls through each unit's public module interface; the web app talks to the backend over HTTP with the walk streamed
B. Shared database tables read directly across units
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: ADR-005; each unit owns its own tables per components.md, and nothing reads another unit's tables directly)

## Consolidated Summary Confirmation

- Eight units by feature area (Q1):
  - U1 knowledge graph and the IBD and urology packs (library), with no dependencies
  - U2 platform: audit, identity and model gateway (library), with no dependencies
  - U3 cases and treatment safety (library), on U1 and U2
  - U4 grounded agent: grounding guard, consult agent and the backend API (service), on U1–U3
  - U5 knowledge updates (library), on U1 and U2
  - U6 prescriptions and follow-up (library, cut first), on U1–U4
  - U7 benchmark (library), on U1–U4
  - U8 doctor web app (ui), on U4–U7
- One local backend process plus the React app; units are modules inside the backend (Q2)
- Units with no dependency between them may be built side by side; Delivery Planning decides the order (Q3)
- Units call each other in-process through their public interfaces and never read each other's tables; the web app talks to the backend over HTTP, with the walk streamed (Q4)

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
