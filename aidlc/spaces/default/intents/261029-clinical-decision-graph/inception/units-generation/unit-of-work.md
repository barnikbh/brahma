# Units of Work — Brahma

Upstream: `components.md` (12 blocks plus the web app), `decisions.md` (ADR-001 – ADR-005), `requirements.md` (priority and cut order), `stories.md` (US1.1–US9.1). Answers: `units-generation-questions.md` Q1–Q4. Walking skeleton is off for this project (`team-practices.md`), so U1 is not shaped as an end-to-end slice.

**Deployment model (Q2):** one local backend process (Python) plus the React web app. Backend units are modules inside that process. Each backend unit that has screens ships its own HTTP router module. U4's server mounts the routers of U1–U4 directly, and mounts U5, U6 and U7 from a configured list of router modules, so U4 never imports them and a cut unit simply isn't listed.

## Units

| Unit ID | Directory | Kind | Components | Complexity | Priority |
|---|---|---|---|---|---|
| U1 | u1-knowledge-graph | library | KnowledgeGraph + pack loader, IBD pack (UC, Crohn's, infectious colitis alternative, safety and response-criterion nodes), urology stub pack | L | Must |
| U2 | u2-platform | library | Audit, Identity, ModelGateway | M | Must |
| U3 | u3-cases-safety | library | Cases, TreatmentSafety | M | Must |
| U4 | u4-grounded-agent | service | GroundingGuard, ConsultAgent, backend HTTP server and streaming | XL | Must |
| U5 | u5-knowledge-updates | library | KnowledgeUpdates (proposals, fetch and drafting, scheduled checks) | M | Must (drafting Should, scheduler Could) |
| U6 | u6-prescriptions-followup | library | Prescriptions, FollowUp | L | Could, cut first |
| U7 | u7-benchmark | library | Benchmark (cases, runner, scoring, resume) | M | Must |
| U8 | u8-web-app | ui | DoctorWebApp (all screens) | XL | Must |

## Unit Details

### U1 — u1-knowledge-graph (library, L)

- **Owns:** Pack, PackVersion, Node, Edge, Source, NodeComment. Loads pack files, rejects a node with no source and names it (FR1.2). Search and traversal on a pinned version, reference ranges by sex, age and pregnancy (FR1.4). Immutable published versions, and a create-version call used by U5.
- **Delivers:** the IBD pack v1.0 (UC and Crohn's at full depth, the infectious-colitis alternative, safety nodes for the demo drugs, and response criteria) and the urology stub pack. The content is drafted with Claude and loaded directly (FR2.6). The content is the largest part of this unit.
- **Notes:** paraphrase and cite only (FR2.5). A load-time check for verbatim runs is advisable (review R-12 from Requirements, accepted as risk).

### U2 — u2-platform (library, M)

- **Owns:** AuditEntry, SessionRecord (append-only, enforced by database triggers plus a test, NFR7); Profile, DisclaimerAcceptance; ModelCallLog.
- **Delivers:** the audit write and query API and export (FR9.2, FR9.4, FR9.5); three seeded profiles plus a system "Benchmark runner" profile; disclaimer acceptance (FR11); the model gateway with provider config, throttling, at most two retries and call logging (FR14, NFR11).
- **Notes:** keys come only from the environment (NFR5). Model calls are stubbed with recorded responses in tests and CI.

### U3 — u3-cases-safety (library, M)

- **Owns:** Patient, Case (with origin and benchmarkRunId), Message, Finding, TreatmentEdit.
- **Delivers:**
  - patients and cases, search, version pin and re-walk check (FR1.7, FR12)
  - chat thread and form state
  - finding validation (FR4.11)
  - the one-tab lock, released on close and expiring after missed heartbeats (domain review R-05)
  - dose computation, safety checks with "Not checked", and treatment edits (FR6, FR1.6)
- **Notes:** dose computation is also called by U4's grounding guard (components.md, R-02).

### U4 — u4-grounded-agent (service, XL)

- **Owns:** Walk, ExploreLane.
- **Delivers:**
  - the grounding guard (claim check including computed doses, FR4.10)
  - the consult agent: extraction, walk, needs-more-data, out-of-knowledge, explore, re-walk, and the "why" (FR4, FR9.3)
  - the backend HTTP server with the walk streamed line by line after each line passes the check
  - session records written to U2
- **Notes:** the most-tested unit. It holds the acceptance tests for the demo walk and the deliberately wrong citation (AC3.2.1, AC3.2.3).

### U5 — u5-knowledge-updates (library, M)

- **Owns:** Proposal, LinkedSource, SourceCheckRun.
- **Delivers:**
  - proposals, and publish and reject by the reviewer profile (FR10.1, FR10.3–FR10.6)
  - source fetch with limits, the verbatim-copy flag and source passages (FR10.9)
  - drafting through the model gateway (FR10.2, Should)
  - the scheduled checker (FR10.7, Could)

### U6 — u6-prescriptions-followup (library, L; Could, cut first)

- **Owns:** Prescription, PrescriptionLine, Visit, MeasureResult.
- **Delivers:**
  - prescription draft, checks, sign, void and PDF (FR7)
  - follow-up visits, trends and verdicts from grounded response criteria (FR8)
- **Notes:** cutting this unit removes it from U4's router list and from U8's navigation, and nothing else changes (ADR-001).

### U7 — u7-benchmark (library, M)

- **Owns:** BenchmarkCase, BenchmarkRun, CaseResult.
- **Delivers:**
  - 20 synthetic cases with expected pathways and reviewer sign-off fields (FR13.1, FR13.7)
  - graph and plain runs, with grounded-share and agreement scoring and the two-part pass (FR13.2–FR13.6)
  - throttled, resumable runs (FR13.8)
  - benchmark cases created through U3 and tagged, so they stay out of History (domain review R-01)

### U8 — u8-web-app (ui, XL)

- **Owns:** no entities.
- **Delivers:**
  - every screen from the handover, with the refined-mockups annotations (A1–A8)
  - chat and map sync on React Flow
  - all screen states, and the five accessibility items (NFR3)
  - the browser smoke test of the demo walk (NFR9)
- **Notes:** screens for U6 appear only when U6 is mounted. U8 has no hard dependency on U6, so U8 is done without it (R-01).

## Assumptions & Open Questions

- [assumption] One SQLite database file is shared by the backend process, with each unit owning its own tables and reading other units only through their interfaces (Q4; domain review R-04).
- [assumption] The IBD content in U1 is the largest single piece of work. Its size, not code, drives U1's complexity.
