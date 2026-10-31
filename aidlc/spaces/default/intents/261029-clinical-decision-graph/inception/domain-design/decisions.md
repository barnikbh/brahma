# Architecture Decisions — Brahma

Upstream: `components.md`, `requirements.md` (priority and cut order, FR4.10, FR13.4, FR14, NFR7), `stories.md`, `team-practices.md`. Answers: `domain-design-questions.md` Q1–Q4.

## ADR-001: Split along requirement groups, with cut-first features as whole blocks

- **Context:** One builder, six days, and an approved cut order that drops prescriptions (FR7) and follow-up (FR8) first (requirements.md, Priority and Cut Order). Whatever is cut must come out without touching Must code.
- **Decision:** Twelve building blocks plus the doctor web app, one per requirement group. Prescriptions and FollowUp are separate blocks that nothing else depends on except the web app.
- **Consequences:** Cutting FR7 or FR8 means removing one block and its screen. There are more block boundaries to write than a coarse split would need, but each is small and in-process (ADR-005).
- **Alternatives Rejected:** Five coarse blocks matching the original idea (knowledge, agent, audit, app, update layer). Cut-first code would be tangled into the agent and app blocks.

## ADR-002: The claim check is its own block (GroundingGuard)

- **Context:** The same claim check is required for answer lines (FR4.10), the plain-language why (FR9.3), follow-up verdicts (FR8.3) and benchmark scoring of both runs (FR13.4). It is the product's core promise.
- **Decision:** A stateless GroundingGuard block that reads KnowledgeGraph. For weight-based doses it asks TreatmentSafety to compute the expected absolute dose, so a claimed "≈ 290 mg" passes only if it matches the node's mg/kg value at the patient's recorded weight. The callers are ConsultAgent, FollowUp and Benchmark.
- **Consequences:** One test suite proves the core promise, including the deliberately wrong citation (AC3.2.3). The benchmark scores the plain model with exactly the same rule as the product, which makes the comparison fair. Every line takes one extra in-process call before it streams.
- **Alternatives Rejected:** Checking inside ConsultAgent. The benchmark and follow-up would need their own copies, and the copies could drift.

## ADR-003: All model calls go through one ModelGateway

- **Context:** The submission must run on the Meta Model API, but credentials aren't available yet. Development uses Claude and a free hosted Llama tier, and the fallback is decided on Nov 2 (FR13.10, FR14).
- **Decision:** A ModelGateway block owns provider selection by configuration, throttling, retries (at most two) and call logging. No other block talks to a provider directly.
- **Consequences:** Switching to Meta is a configuration change. Rate limits and errors are handled in one place (FR13.8, FR14.4). Every audit entry and benchmark run can name its provider and model. Provider-specific features are limited to what the gateway exposes.
- **Alternatives Rejected:** Calling provider SDKs from each block. Switching would touch four blocks on the day the Meta credentials arrive.

## ADR-004: Cases owns the live record; Audit owns the immutable one

- **Context:** The chat, findings and form drafts change while a case is open (FR12.3). The audit must never change (FR9.2, NFR7), and append-only has to be enforceable on a local database.
- **Decision:** Cases owns Patient, Case, Message and Finding, including the version pin and the tab lock. Audit owns AuditEntry and SessionRecord, has no update or delete path, and every other block writes to it only through Audit.
- **Consequences:** Append-only can be enforced and tested in one block (database triggers plus a test). Some data is written twice: the chat lives in Cases, and the session snapshot lives in Audit. That duplication is deliberate: the audit holds what was shown at the time.
- **Alternatives Rejected:** Audit owning the whole session including the chat. That would need update paths in the block that must never update.

## ADR-005: In-process calls in one local app; the walk streams to the web app

- **Context:** The app runs locally for one doctor (team-practices.md, Deployment). Progress must appear within 3 seconds (NFR1).
- **Decision:** Backend blocks call each other directly in process. The web app calls the backend synchronously, except for the walk, which streams checked lines as they pass GroundingGuard. Deployment shape is left to Units Generation.
- **Consequences:** No queue or service mesh to set up, and failures surface as typed errors at the call site. Scaling to many doctors would need a later redesign, which is out of scope.
- **Alternatives Rejected:** Events through a message queue. It adds setup cost and moving parts with no benefit for one local user.
