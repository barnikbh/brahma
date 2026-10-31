# Contract Summary — Brahma

Upstream: `unit-of-work.md` (U1–U8, kinds), `unit-of-work-dependency.md` (DAG edges and the router-mount rule), `components.md` (entity shapes), `requirements.md` (FR4.10, FR5.9, FR9.2, FR13, FR14.4, NFR1, NFR5, NFR8). Answers: `contract-design-questions.md` Q1–Q4.

No public API is exposed (Q1). Every contract is internal: backend unit to backend unit through typed Python interfaces with shared Pydantic models, and backend to web app over local HTTP (Q2). Field names below are the contract. Types are indicative; Functional Design pins full schemas.

## Contracts

| # | Provider Unit | Consumer | Mechanism | Owner |
|---|---|---|---|---|
| C1 | u1-knowledge-graph | u3, u4, u5, u6, u7 | Python interface + shared models | U1 |
| C2 | u2-platform (Audit) | u3, u4, u5, u6, u7 | Python interface | U2 |
| C3 | u2-platform (Identity) | u5, u6, u8 (via C8) | Python interface | U2 |
| C4 | u2-platform (ModelGateway) | u4, u5, u6, u7 | Python interface | U2 |
| C5 | u3-cases-safety | u4, u6, u7 | Python interface | U3 |
| C6 | u4-grounded-agent (GroundingGuard, Walk) | u6, u7 | Python interface | U4 |
| C7 | u5, u6, u7 | u4 server | Router-mount convention | U4 |
| C8 | u4-grounded-agent (HTTP server) | u8-web-app | REST JSON + Server-Sent Events | U4 |
| C9 | u5-knowledge-updates | u8-web-app | REST JSON (mounted on C8 server) | U5 |
| C10 | u6-prescriptions-followup (optional) | u8-web-app | REST JSON (mounted on C8 server) | U6 |
| C11 | u7-benchmark | u8-web-app | REST JSON (mounted on C8 server) | U7 |
| X1 | External: Meta Model API, Claude API, free hosted Llama | u2 ModelGateway (consumer) | HTTPS, provider SDKs | Provider (consumed only) |
| X2 | External: public web (source URLs) | u5 (consumer) | HTTPS GET with limits | Consumed only |

## C1 — Knowledge graph interface (U1)

```yaml
# shared-schema: Python Protocol + Pydantic models, module brahma.knowledge
models:
  PackVersionRef: { pack: str, number: str }            # e.g. {pack: "IBD", number: "1.3"}
  Source: { sourceId: str, title: str, year: int, section: str, url: "str|null" }
  Node:
    nodeId: str
    packVersion: PackVersionRef
    type: "symptom|metric|diagnosis|subtype|test|treatment_tier|drug|monitoring|response_criterion|diet|watch_out|escalation|interaction|allergy_cross_reactivity"
    label: str
    content: str
    fields: dict            # structured claims, e.g. {drug, route, dose_value, dose_unit, dose_basis: "absolute|per_kg", rounding, frequency, duration, threshold}
    sourceIds: [str]        # never empty (FR1.2)
    plausibleRange: "dict|null"
    referenceRanges: "list|null"   # [{sex, ageBand, pregnancy, low, high, unit}]
  Edge: { edgeId: str, fromNodeId: str, toNodeId: str, relation: str, condition: "dict|null" }
operations:
  load_pack(path) -> PackVersionRef           # raises PackLoadError(nodeId, reason) on a node with no source
  live_version(pack) -> PackVersionRef
  get_node(version, nodeId) -> Node            # raises NodeNotFound
  search(version, facts: [Fact]) -> { matches: [Node], unknownUnit: [Fact] }      # Fact = {kind: finding|test, name, value?, unit?} (U1 functional design)
  neighbours(version, nodeId, facts: [Fact], relation?) -> [Step]                 # Step = {edge, node, status: followable|not_taken|alternative|unknown_input}
  match_claims(node, claims: [Claim]) -> { matched: [Claim], failures: [{claim, reason}] }   # U1 owns claim matching; C6 check_line uses it
  list_versions(pack) -> [PackVersion]                                            # for U5 version history
  reference_range(version, nodeId, sex, age, pregnancy) -> "Range|null"
  sources(version) -> [Source]
  find_supporting_node(version, sourceId, claims: [Claim]) -> "Node|null"   # R-03: plain-run scoring, see C6
  subgraph(version, nodeIds) -> { nodes: [Node], edges: [Edge] }           # R-02: map data for a walk or replay
  list_comments(nodeId) -> [NodeComment]                                   # R-01
  add_comment(nodeId, authorProfileId, text) -> commentId                  # R-01
  create_version(pack, base, changes: ChangeSet, publishedBy) -> PackVersionRef   # only caller: U5 publish; ChangeSet per U1 entities.md
rules:
  - Published versions are immutable; every read names a version (FR1.7).
  - Node and source IDs are pack-prefixed and globally unique (e.g. IBD-N12), so comments and references never collide across packs.
```

## C2 — Audit interface (U2)

```yaml
# shared-schema: module brahma.platform.audit
models:
  AuditEntryIn: { kind: str, caseId: "str|null", sessionId: "str|null", profileId: str, packVersion: "PackVersionRef|null", provider: "str|null", model: "str|null", payload: dict }
  SessionRecordIn: { caseId: str, walkId: str, profileId: str, packVersion: str, provider: str, model: str, inputs: { text: str, findings: [dict] }, pathNodeIds: [str], answer: { summary: str, sections: [dict], counts: dict }, sources: [str], explanation: [dict], outcome: "answered|needs_data|out_of_knowledge|error", benchmarkRunId: "str|null" }   # profileId, packVersion, provider, model added (U2 functional design review)
operations:
  append(entry: AuditEntryIn) -> entryId
  record_session(record: SessionRecordIn) -> sessionId
  list_sessions(filter: {outcome?, text?, includeBenchmark: bool = false, benchmarkRunId?}) -> [SessionSummary]   # benchmarkRunId implies includeBenchmark (R-01)
  get_session(sessionId) -> SessionRecord
  export_session(sessionId, format: "json|pdf") -> bytes
rules:
  - No update or delete operation exists; the database rejects UPDATE and DELETE on audit tables (FR9.2, NFR7).
  - walkId is a plain identifier; U2 never imports U4.
  - Each write is one transaction.
```

## C3 — Identity interface (U2)

```yaml
# shared-schema: module brahma.platform.identity
models:
  Profile: { profileId: str, displayName: str, role: "doctor|reviewer|system", specialty: "str|null", demoRegistration: "str|null" }
operations:
  list_profiles() -> [Profile]          # three demo profiles; the system profile is not listed
  get_profile(profileId) -> Profile
  needs_disclaimer(profileId, disclaimerVersion, packVersions: str) -> bool   # packVersions format "IBD 1.3; URO 0.1", packs sorted by code; caller (U4 server) passes the live versions from U1
  accept_disclaimer(profileId, disclaimerVersion, packVersions: str) -> acceptanceId
  require_role(profileId, role) -> None # raises Forbidden
```

## C4 — Model gateway interface (U2)

```yaml
# shared-schema: module brahma.platform.models
models:
  ModelRequest: { purpose: "extract|narrate|explain|draft|plain_benchmark|followup", messages: [dict], maxTokens: int, responseSchema: "dict|null" }
  ModelResponse: { text: str, parsed: "dict|null", provider: str, model: str, latencyMs: int, inputTokens: "int|null", outputTokens: "int|null" }
operations:
  current() -> { provider: str, model: str }
  complete(request: ModelRequest) -> ModelResponse
errors:
  ModelTimeout | ModelRateLimited | ModelAuthError | ModelUnavailable   # each carries provider and retryable
rules:
  - The provider is chosen by environment configuration only (FR14.1); keys only from the environment (NFR5).
  - Throttles to the provider's limit; retries at most twice, then raises (FR14.4). No other unit retries.
  - Every call is logged to ModelCallLog (NFR11).
  - Tests and CI use a recorded-response provider; no network or keys.
```

## C5 — Cases and safety interface (U3)

```yaml
# shared-schema: module brahma.cases
models:
  Patient: { patientId: str, syntheticName: str, age: int, sex: "female|male|unknown", weightKg: "float|null", pregnancyStatus: "str|null", comorbidities: [str], allergies: [str], currentMedication: [str] }
  Case: { caseId: str, patientId: str, ownerProfileId: str, pinnedPackVersion: "PackVersionRef|null", origin: "clinic|benchmark", benchmarkRunId: "str|null", status: str }
  Finding: { findingId: str, kind: str, name: str, value: "float|str|null", unit: "str|null", enteredValue: "str|null", duration: "str|null", validationState: "ok|invalid|conflict|confirm_range" }
  SafetyResult: { check: "allergy|pregnancy|interaction|duplicate_class", status: "ok|conflict|not_checked", nodeIds: [str], message: str }
  Message: { messageId: str, caseId: str, author: "doctor|brahma|system", kind: "text|form|form_answer|pathway|map_action", body: dict, formKind: "str|null", formState: "open|submitted|null", createdAt: str }
operations:
  search_patients(query: str, ownerProfileId) -> [CaseSummary]   # case ID, finding or diagnosis; excludes origin=benchmark (R-01)
  create_case(patient, ownerProfileId, origin="clinic", benchmarkRunId=None) -> Case
  get_case(caseId) -> Case
  get_patient(caseId) -> Patient                                  # R-01
  update_patient(caseId, changes: dict, editorProfileId) -> Patient   # FR4.9; caller re-reads ranges and doses (R-01)
  pin(caseId, version) -> None
  newer_version(caseId) -> "PackVersionRef|null"
  append_message(caseId, message) -> messageId
  list_messages(caseId) -> [Message]                              # R-01
  save_form_draft(caseId, messageId, values: dict) -> None        # unsubmitted form values, FR12.3 (R-01)
  get_form_drafts(caseId) -> {messageId: values}                  # R-01
  set_findings(caseId, findings) -> [Finding]     # runs FR4.11 validation
  acquire_lock(caseId, tabId) -> "held|read_only"  # heartbeat-based expiry
  release_lock(caseId, tabId) -> None                             # R-01
  compute_dose(caseId, nodeId) -> { value: float, unit: str, formula: str } | MissingWeight
  safety_checks(caseId, drugNodeIds) -> [SafetyResult]   # never "ok" without a node (FR1.6)
  apply_edit(caseId, nodeId, newValues, editorProfileId) -> TreatmentEdit
```

## C6 — Grounding and walk interface (U4)

```yaml
# shared-schema: module brahma.agent
models:
  Claim: { kind: "diagnosis|test|drug|dose|frequency|duration|threshold|tier", value: str, unit: "str|null" }
  CheckResult: { passed: bool, claims: [Claim], failures: [{claim: Claim, reason: str}] }
  WalkResult: { walkId: str, outcome: "answered|needs_data|out_of_knowledge|error", sections: [dict], counts: {steps: int, cited: int, ungrounded: int}, pathNodeIds: [str] }
operations:
  check_line(text, citedNodeIds, version, caseId) -> CheckResult     # FR4.10; uses C5.compute_dose for per-kg doses
  check_line_by_source(text, citedSourceIds, version, caseId) -> CheckResult   # R-03: plain-run scoring
  run_walk(caseId, findings, answers?) -> WalkResult                 # for U7; same logic as the streamed walk
rules:
  - A line is emitted only if check_line passed; failures increment ungrounded and are written to the audit.
  - "check_line_by_source (R-03): extracts the line's claims, then for each cited source asks C1.find_supporting_node(version, sourceId, claims). The line passes only when one node under a cited source supports every claim, by the same matching rules as check_line. A line citing no source, or a source not in the pack, fails. U7 scores the graph run with check_line and the plain run with check_line_by_source, so both use the same claim matching (FR13.4)."
```

## C7 — Router mount convention (U4 owns; U5, U6, U7 follow)

```yaml
# shared-schema: convention
contract:
  each_unit_exposes: "module attribute `router` (an HTTP router) and `feature` = {name, version, screens: [str]}"
  server_config: "BRAHMA_FEATURE_MODULES=brahma.updates.api,brahma.rx_followup.api,brahma.benchmark.api"
  mount_path: "/api/<feature name>"
  discovery: "GET /api/features lists mounted features; the web app shows only their screens (R-01)"
rules:
  - A module missing from the config is simply not mounted; nothing else changes.
```

## C8 — Core HTTP API (U4 server → U8)

```yaml
openapi: 3.0.3
info: { title: Brahma core API, version: "1.0" }
paths:
  /api/features:            { get: { summary: Mounted features } }
  /api/profiles:            { get: { summary: Demo profiles (C3) } }
  /api/session:             { post: { summary: Sign in as a profile, body: { profileId } } }
  /api/disclaimer:          { post: { summary: Accept disclaimer } }
  /api/patients:            { get: { summary: Search, params: [q] }, post: { summary: Create patient and case } }
  /api/cases/{caseId}:      { get: { summary: Case, card, thread, map state, pin, newer version } }
  /api/cases/{caseId}/lock: { post: { summary: Acquire or heartbeat the tab lock } }
  /api/cases/{caseId}/messages: { post: { summary: Send a chat message or a form answer } }
  /api/cases/{caseId}/walk:
    post:
      summary: Start or continue a walk; responds with a Server-Sent Events stream
      events:
        progress: { step: str }
        form: { kind: "confirm-findings|needs-data|edit-treatment|patient-details", fields: [object] }
        line: { sectionId: str, text: str, nodeIds: [str] }      # sent only after check_line passed
        section_done: { sectionId: str }
        done: { outcome: str, counts: { steps: int, cited: int, ungrounded: int }, packVersion: str, provider: str, model: str }
        error: { code: str, message: str, retryable: bool }
  /api/nodes/{version}/{nodeId}: { get: { summary: Node detail with sources, comments, safety for this case, params: [caseId] } }
  /api/cases/{caseId}/treatment-edits: { post: { summary: Apply a treatment edit } }
  /api/sessions:            { get: { summary: History list, params: [outcome, q, includeBenchmark] } }
  /api/sessions/{sessionId}: { get: { summary: Session audit detail and replay data } }
  /api/sessions/{sessionId}/export: { get: { summary: Export, params: [format] } }
components:
  schemas:
    Error: { type: object, required: [code, message, retryable], properties: { code: { type: string }, message: { type: string }, retryable: { type: boolean } } }
```

- Every HTTP error uses `Error`. Model errors arrive as `error` events with `retryable` (Q4).
- The SSE stream sends the first `progress` event within 3 seconds (NFR1).

### C8 additions (R-02)

```yaml
openapi: 3.0.3
info: { title: Brahma core API — walk, map and response shapes, version: "1.0" }
paths:
  /api/cases/{caseId}/walk:
    post:
      requestBody:
        WalkRequest:
          mode: "start|continue|rewalk|explore|stop_explore"
          text: "string|null"            # start: the doctor's free text
          formMessageId: "string|null"   # continue: the form being answered
          formValues: "object|null"      # continue: confirmed chips or test results
          branchNodeId: "string|null"    # explore and stop_explore: the alternative node
          walkId: "string|null"          # continue, explore, stop_explore: the walk being resumed
      responses:
        "200": text/event-stream (events below)
        "409": Error code "case_read_only" when this tab doesn't hold the case lock
  /api/cases/{caseId}/map:
    get:
      summary: Map data for the case's latest walk, or for a session when replaying
      params: [walkId?, sessionId?]
      responses: { "200": MapData }
  /api/cases/{caseId}/patient:
    patch: { summary: Change patient details (FR4.9), body: PatientChanges, responses: { "200": CaseView } }
  /api/cases/{caseId}/forms/{messageId}/draft:
    put: { summary: Save unsubmitted form values (FR12.3), body: object }
  /api/cases/{caseId}/lock:
    post:   { summary: Acquire or heartbeat, body: { tabId }, responses: { "200": { state: "held|read_only" } } }
    delete: { summary: Release on tab close, body: { tabId } }
  /api/nodes/{version}/{nodeId}/comments:
    get:  { responses: { "200": [NodeComment] } }
    post: { body: { text }, responses: { "201": NodeComment } }
components:
  schemas:
    CaseView: { case: Case, patient: Patient, messages: [Message], formDrafts: object, pinnedVersion: string, newerVersion: "string|null", lock: "held|read_only" }
    CaseSummary: { caseId: string, label: string, status: "follow_up_due|needs_data|out_of_knowledge|plan_in_place|new", updatedAt: string }
    MapData: { version: string, nodes: [MapNode], edges: [MapEdge], selectedPath: [string], exploreLanes: [{ laneId: string, nodeIds: [string] }] }
    MapNode: { nodeId: string, type: string, label: string, column: "findings|diagnosis|tests|subtype|treatment|monitor", status: "used|entry|test_needed|not_in_pack|bypassed|not_taken|exploring", result: "object|null" }
    MapEdge: { edgeId: string, from: string, to: string, style: "walked|bypassed|not_taken|exploring" }
    NodeDetail: { node: Node, sources: [Source], comments: [NodeComment], safety: [SafetyResult], dose: "object|null", edited: "TreatmentEdit|null" }
    SessionSummary: { sessionId: string, caseId: string, createdAt: string, label: string, outcome: string, packVersion: string }
    SessionDetail: { record: SessionRecord, map: MapData, entries: [AuditEntry] }
    PatientChanges: { sex?: string, weightKg?: number, pregnancyStatus?: string, comorbidities?: [string], allergies?: [string] }
```

**Walk event flow (R-02)**

1. `start` with the doctor's text. The stream emits `progress`, then a `form` event with `kind: confirm-findings` and its `messageId`, then `paused` (`{ walkId, waitingFor: messageId }`), and closes.
2. `continue` with that `formMessageId` and the confirmed values. A new stream walks on and emits `progress`, `map_update`, checked `line` events and `section_done` per section. It ends with either another `form` (needs-data) and `paused`, or `done`.
3. `explore` or `stop_explore` with `branchNodeId` streams `map_update` and checked `line` events into a separate lane (`laneId`), and never changes the main sections.
4. `rewalk` starts a new walk on the case's findings and history. If a newer pack version is live, it uses that version and records both.

**Extra events:**
- `map_update`: `{ nodes: [MapNode], edges: [MapEdge] }`, sent as nodes light up.
- `paused`: `{ walkId, waitingFor }`.

`progress.step` is a fixed label from a closed list (`reading_findings`, `matching_diagnosis`, `refining`, `planning_treatment`, `checking_sources`, `writing_explanation`). It never carries model text, because only checked lines may show model output.

**Failure mid-stream:**
- If the model gateway or a check fails after some lines were sent, the stream emits `error` (`code`, `message`, `retryable`) and closes.
- Lines already sent stay; nothing is withdrawn.
- The walk is saved as `error` with its progress. Retry is `continue` with the same `walkId`, which resumes after the last completed section and keeps every input (FR5.9).
- If the connection drops without an `error`, the web app calls `GET /api/cases/{caseId}`, which returns the walk state, and offers Retry.

## C9 — Knowledge API (U5 → U8)

```yaml
openapi: 3.0.3
info: { title: Brahma knowledge API, version: "1.0" }
paths:
  /api/knowledge/proposals:            { get: { summary: List proposals }, post: { summary: Create proposal (node, source url or upload, section, change, comment) } }
  /api/knowledge/proposals/{id}:       { get: { summary: Before, after, source passages, copy flags } }
  /api/knowledge/proposals/{id}/publish: { post: { summary: Reviewer publishes, body: { comment } } }
  /api/knowledge/proposals/{id}/reject:  { post: { summary: Reviewer rejects, body: { comment } } }
  /api/knowledge/versions:             { get: { summary: Version history per pack } }
```

- Publish and reject return `403 Error` unless the session profile has the reviewer role. A proposal with copy flags returns `409 Error` on publish.

## C10 — Prescriptions and follow-up API (U6 → U8, optional)

```yaml
openapi: 3.0.3
info: { title: Brahma rx and follow-up API, version: "1.0" }
paths:
  /api/rx-followup/cases/{caseId}/prescriptions:  { post: { summary: Draft from plan } }
  /api/rx-followup/prescriptions/{id}:            { get: { summary: Draft or signed with checks }, patch: { summary: Edit lines } }
  /api/rx-followup/prescriptions/{id}/sign:       { post: { summary: Sign; 409 when blocked; body: { acknowledgements } } }
  /api/rx-followup/prescriptions/{id}/void:       { post: { summary: Void with reason; returns new draft id } }
  /api/rx-followup/prescriptions/{id}/pdf:        { get: { summary: PDF } }
  /api/rx-followup/cases/{caseId}/visits:         { get: { summary: Visits and trends }, post: { summary: Record results; returns verdict } }
```

## C11 — Benchmark API (U7 → U8)

```yaml
openapi: 3.0.3
info: { title: Brahma benchmark API, version: "1.0" }
paths:
  /api/benchmark/runs:          { get: { summary: Runs with provider, model, date }, post: { summary: Start or resume a run } }
  /api/benchmark/runs/{runId}:  { get: { summary: Totals, grounded share and agreement for both modes, per-case results, pass } }
```

## External Boundaries (consumed only)

| # | Boundary | Rules |
|---|---|---|
| X1 | Model providers | Only U2 ModelGateway calls them; keys from the environment; at most two retries; typed errors (C4) |
| X2 | Source URLs | Only U5 fetches; http(s) only; local and private addresses refused; 10 MB and 20 s caps; text treated as data, never instructions (FR10.9) |

## Contract Ownership Rules

- The provider unit owns each contract and its contract test (Q3).
- One repo, one builder: a breaking change lands in the same commit as every consumer's update, with the contract test changed first.
- Additive changes are always safe: consumers ignore unknown fields, and new SSE event types are ignored by older clients.
- Shared Pydantic models live in the provider unit's module; consumers import them, never copy them.
- Only U2 ModelGateway retries. Everything else surfaces typed errors at once (Q4, NFR8).

## Open Questions

| Contract | Question | Blocks |
|---|---|---|
| C4 | Does the Meta Model API support a structured-output (JSON schema) mode like `responseSchema`, or must extraction parse text? | u4-grounded-agent (extraction), u5 (drafting) |
| C8 | Is the tab-lock heartbeat interval 15 s with a 45 s expiry acceptable for the demo? | u3-cases-safety, u8-web-app |
| C1 | Pack file format (YAML or JSON) for hand-authored content | u1-knowledge-graph |
