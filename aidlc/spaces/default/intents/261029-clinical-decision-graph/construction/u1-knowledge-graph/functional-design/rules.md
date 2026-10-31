# Business Rules — u1-knowledge-graph

Upstream: `requirements.md` (FR1, FR2, FR3), `stories.md` (US3.2, US3.6, US8.2, US9.1), `contract-summary.md` (C1), `entities.md`.

```yaml
rules:
  - id: BR1.1
    statement: A pack cannot load if any node has no source.
    category: validation
    applies_to: Pack load
    trigger: load_pack
    logic: IF any Node.sourceIds is empty OR names a Source not in the pack THEN reject the whole load
    violation: PackLoadError naming the nodeId and the reason; nothing is stored
    source: FR1.2
  - id: BR1.2
    statement: Edges must connect nodes of the same version and never a node to itself; edge conditions must reference findings or tests that exist as nodes in the same version.
    category: validation
    applies_to: Pack load
    trigger: load_pack, create_version
    logic: IF an edge end is missing, crosses versions, or is a self-edge, OR a condition names something that is not the name of a symptom, metric or test node in the same version THEN reject the load. Node and source IDs must start with the pack's code and be unique across all packs.
    violation: PackLoadError naming the edgeId
    source: FR1.3
  - id: BR1.3
    statement: Published versions are immutable; a change produces a new version and the previous live version becomes superseded.
    category: constraint
    applies_to: PackVersion
    trigger: create_version
    logic: >
      IF create_version is called THEN copy the base version, apply the ChangeSet, run BR1.1, BR1.2, BR1.4 and
      BR3.5 on the result, give it the next minor number, mark it live and mark the old live version superseded,
      in one transaction. IF load_pack names a pack that already exists THEN the file's version number must be
      higher than the live one; it is stored as the new live version and the old one is superseded, with the
      file's changeSummary (or "Initial load" for a pack's first load). A repeated or lower number is refused.
      list_versions(pack) returns every version with number, status, publishedAt, publishedBy and changeSummary,
      newest first.
    violation: on any failure nothing changes and the error is returned; a repeated or lower number is VersionNotIncreasing
    source: FR1.5, FR10.5, FR10.6
  - id: BR1.4
    statement: Each node type carries its required structured fields so claims can be checked against them.
    category: validation
    applies_to: Node
    trigger: load_pack, create_version
    logic: IF a node lacks a required FieldSchema key for its type (e.g. drug without doseValue, doseUnit, doseBasis) THEN reject the load
    violation: PackLoadError naming the nodeId and missing key
    source: FR1.2, FR4.10
  - id: BR1.5
    statement: Every read names a version; reads never mix versions.
    category: constraint
    applies_to: all read operations
    trigger: any read
    logic: IF a read omits the version THEN refuse
    violation: VersionRequired error
    source: FR1.7
  - id: BR1.6
    statement: The model is specialty-agnostic; packs differ only in data.
    category: policy
    applies_to: Pack
    trigger: load_pack
    logic: Packs for any specialty load through the same loader and node types; no specialty-specific code paths exist
    violation: n/a (design constraint, tested by loading the urology stub)
    source: FR1.1, FR3.1
  - id: BR2.1
    statement: Search returns nodes matching confirmed findings by name or synonym and metric thresholds by value and unit.
    category: calculation
    applies_to: search
    trigger: search(version, facts)
    logic: >
      A finding matches a symptom node when its name, lowercased and trimmed, equals the node's name or one of its
      synonyms, and its duration meets durationMin if set. A metric finding matches a metric node by measure name
      when its value, converted to the node's canonical unit, meets the node's threshold and comparator.
      Unit conversion uses one fixed table per measure, for example Hb g/L to g/dL divides by 10, and calprotectin
      mg/kg equals ug/g. A unit not in the table for that measure never matches: the fact is returned in the result
      as unknown_unit so the caller can ask the doctor.
    violation: no match returns an empty list (the caller reports out of knowledge)
    source: FR4.2, FR4.5
  - id: BR2.2
    statement: neighbours takes the case's facts and returns every outgoing edge as a Step with a status saying whether it can be followed.
    category: calculation
    applies_to: neighbours
    trigger: neighbours(version, nodeId, facts, relation?)
    logic: >
      For each outgoing edge, IF it has no condition, OR a fact with the condition's name satisfies its comparator
      after BR2.1 unit conversion, THEN status followable. IF the condition's fact is missing THEN status
      unknown_input (the caller asks for that test). IF the fact is present but does not satisfy it THEN status
      not_taken.
    violation: n/a
    source: FR1.3, FR4.4, FR4.6
  - id: BR2.3
    statement: Alternative branches are returned as Steps with status alternative so the map can show and explore them.
    category: calculation
    applies_to: neighbours, subgraph
    trigger: read
    logic: Edges with relation alternative_to, and nodes with alternative=true, get status alternative, whatever the facts say
    violation: n/a
    source: FR2.7, FR4.7
  - id: BR2.4
    statement: Reference ranges are picked by the patient's sex, then age band and pregnancy; if sex is unknown, the widest range is used and flagged.
    category: calculation
    applies_to: reference_range
    trigger: reference_range(version, nodeId, sex, age, pregnancy)
    logic: >
      A range matches when each attribute it sets (sex, ageBand, pregnancy) equals the patient's; attributes it
      leaves unset match anything. The most specific match is the one setting the most attributes; ties go to
      sex, then pregnancy, then ageBand. IF sex is unknown THEN, among ranges that match on the other attributes,
      choose the widest (largest high minus low; an open end counts as widest) and return the flag
      sex_not_recorded.
    violation: no range returns null
    source: FR1.4
  - id: BR2.5
    statement: U1 owns claim matching. match_claims compares claims with one node's fields; find_supporting_node uses it to find a node under a cited source.
    category: calculation
    applies_to: match_claims, find_supporting_node
    trigger: claim checks (called by U4's grounding guard) and plain-run scoring
    logic: >
      match_claims(node, claims) passes a claim only when its kind maps to a field of the node's type and the
      values are equal: text after lowercasing, trimming and resolving synonyms (drug synonyms, symptom
      synonyms); numbers exactly, after BR2.1 unit conversion to the field's unit. A dose claim matches doseValue
      and doseUnit only when doseBasis is absolute. Per-kg doses are resolved by U4 with U3's dose computation
      before calling, and passed as an already-computed absolute claim with the node's per-kg value as evidence.
      It returns {matched: [claims], failures: [{claim, reason}]}. find_supporting_node(version, sourceId, claims)
      returns the first node, in nodeId order, citing that source for which match_claims has no failures; else
      null.
    violation: failures list the reason (no field for kind, value differs, unit unknown)
    source: FR4.10, FR13.4
  - id: BR2.6
    statement: subgraph returns the requested nodes, the edges among them, and each node's column for the map.
    category: calculation
    applies_to: subgraph
    trigger: map data request
    logic: Return nodes by id with column and alternative flag; include edges whose both ends are in the set
    violation: unknown ids are listed as missing
    source: FR5.2
  - id: BR2.7
    statement: Comments attach to a pack-prefixed nodeId and show across versions of that pack only.
    category: policy
    applies_to: NodeComment
    trigger: add_comment, list_comments
    logic: Store by the globally unique nodeId; list newest first; text 1-1000 chars; an unknown nodeId is refused
    violation: invalid text is refused
    source: FR1.2
  - id: BR3.1
    statement: The IBD pack contains the ulcerative colitis branch at full depth.
    category: policy
    applies_to: IBD pack content
    trigger: content authoring
    logic: Findings (bloody stool, Hb, calprotectin) -> IBD -> tests (stool culture, colonoscopy with biopsy, extent, severity) -> UC sub-types by extent (E1-E3) and severity -> tiers 1-3 with entry criteria -> monitoring, diet, watch-outs, surgery triggers; the demo case reaches pancolitis severe at Tier 2
    violation: the content test for the demo case fails
    source: FR2.1
  - id: BR3.2
    statement: The IBD pack contains the Crohn's disease branch at the same depth.
    category: policy
    applies_to: IBD pack content
    trigger: content authoring
    logic: Crohn's sub-types (location and behaviour) and severity -> tiers with entry criteria -> monitoring, diet, watch-outs, surgery triggers
    violation: the Crohn's content test fails
    source: FR2.2
  - id: BR3.3
    statement: The IBD pack includes the infectious-colitis alternative and safety and response-criterion nodes for every demo drug and tier.
    category: policy
    applies_to: IBD pack content
    trigger: content authoring
    logic: Infectious colitis as alternative_to IBD with its tests; drug nodes for mesalamine, methylprednisolone, hydrocortisone, infliximab, ustekinumab, levothyroxine with classes and contraindications; penicillin allergy class; response criteria per tier
    violation: content test fails
    source: FR2.3, FR2.7, FR1.6
  - id: BR3.4
    statement: A urology stub pack with a handful of nodes loads through the same model.
    category: policy
    applies_to: Urology pack content
    trigger: content authoring
    logic: At least one walkable path from a finding to a plan, cited
    violation: content test fails
    source: FR3.1, FR3.2
  - id: BR3.5
    statement: Every dose, frequency and duration in the content comes from the cited source; placeholders are not allowed anywhere in a loaded pack.
    category: validation
    applies_to: all nodes
    trigger: load_pack, create_version
    logic: IF any node field or content holds a bracketed placeholder (text in square brackets such as [x] or [60 mg]) THEN reject the load
    violation: PackLoadError naming the node and field
    source: FR2.4
  - id: BR3.6
    statement: Content is paraphrased; long verbatim runs from a source are caught before the pack is loaded.
    category: policy
    applies_to: IBD and urology pack content
    trigger: content authoring, before load
    logic: >
      Source text is not stored in U1, so a load can't detect copying. Instead, the content-authoring check
      compares each node's content with the cited source passage the author used, kept outside the pack, and
      flags any run of more than 25 consecutive words. Flagged content is rewritten before load. Owner: you,
      with your reviewer's content check (external-dependency-map.md). Proposals after v1.0 are checked by U5
      (FR10.9).
    violation: content not loaded until rewritten
    source: FR2.5, C-R4
```

## Summary

| ID | Category | Rule | Source |
|---|---|---|---|
| BR1.1 | validation | No source, no load | FR1.2 |
| BR1.2 | validation | Edges well-formed; IDs pack-prefixed and unique | FR1.3 |
| BR1.3 | constraint | Versions immutable; changes and re-loads make a new version; list versions | FR1.5, FR10.5, FR10.6 |
| BR1.4 | validation | Node types carry their structured fields | FR1.2, FR4.10 |
| BR1.5 | constraint | Every read names a version | FR1.7 |
| BR1.6 | policy | One model for every specialty | FR1.1, FR3.1 |
| BR2.1 | calculation | Search by finding name and metric threshold | FR4.2, FR4.5 |
| BR2.2 | calculation | Steps with followable, not-taken or unknown-input status from the case's facts | FR1.3, FR4.4, FR4.6 |
| BR2.3 | calculation | Alternatives returned with status alternative | FR2.7, FR4.7 |
| BR2.4 | calculation | Reference range by sex, age and pregnancy, with precedence and widest defined | FR1.4 |
| BR2.5 | calculation | U1 owns claim matching; supporting node under a source | FR4.10, FR13.4 |
| BR2.6 | calculation | Subgraph for the map | FR5.2 |
| BR2.7 | policy | Comments by nodeId | FR1.2 |
| BR3.1 | policy | UC branch at full depth | FR2.1 |
| BR3.2 | policy | Crohn's branch at the same depth | FR2.2 |
| BR3.3 | policy | Alternative, safety and response nodes | FR2.3, FR2.7, FR1.6 |
| BR3.4 | policy | Urology stub | FR3.1, FR3.2 |
| BR3.5 | validation | No placeholders anywhere in loaded content | FR2.4 |
| BR3.6 | policy | Verbatim-copy check before load, owned by you and your reviewer | FR2.5, C-R4 |
