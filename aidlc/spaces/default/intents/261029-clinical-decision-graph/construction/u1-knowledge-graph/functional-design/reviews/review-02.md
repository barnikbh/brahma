## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-29T14:10:59Z
**Iteration:** 2
**Verdict Dictated:** no

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/rules.md > BR2.2 and BR2.3; functional-spec.md > W2 | BR2.2 decides whether an edge is followable from "the case's findings and results", and BR2.3 returns edges with status `not_taken`. The contract operation is `neighbours(version, nodeId, relation?) -> [(Edge, Node)]`: it takes no findings or results, and Edge has no status field. A developer cannot implement the specified behaviour against the contract as written. | Decide where the case's findings and results enter (a findings/results parameter on `neighbours`, or return all edges with their conditions and let U4 evaluate them). Define the return shape that carries `followable` or `not_taken` per edge. Record the needed change to the contract. Define the finding/result input type, since FindingRef is not defined anywhere. | Resolved (reviewer) |
| R-02 | Major | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/rules.md > BR2.1; entities.md > FieldSchema | BR2.1 matches a symptom node "by name or listed synonym", but no synonym attribute exists on Node or in FieldSchema. FieldSchema also has no entry for `symptom`, so BR1.4 has no required keys for it. Metric matching "after unit normalisation" has no stated unit rules. Entry-point search (AC3.2.1) cannot be built or tested without guessing. | Add a `symptom` field schema (name, synonyms) and a required-keys list for every node type, including `symptom`, `escalation`, `diet` and `watch_out`. State the unit-normalisation behaviour (convertible units, and what happens on an unknown unit). | Resolved (reviewer) |
| R-03 | Major | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/rules.md > BR2.5; functional-spec.md > W5 | BR2.5 says U1 matches claims "by the C6 matching rules", and W5 says U4's rules decide support while U1 supplies candidates. But C6 says U4 calls `C1.find_supporting_node` to do the matching, and U1 declares no dependencies. The claim-matching logic therefore has no owner, and U1 would need U4's matcher (a reverse dependency). The operation returns a single node, so it cannot return "candidates". | Make U1 own a concrete, self-contained matching rule (for example exact numeric equality of value and unit, normalised drug name, tier equality) written in BR2.5, or change the contract so U4 supplies the matcher or fetches candidates and does the matching itself. Remove the reference to C6 from U1's rules. | Resolved (reviewer) |
| R-04 | Major | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/entities.md > Node.nodeId, NodeComment.nodeId | nodeId is unique only within a version, with stable IDs such as N12. Two packs (IBD and the urology stub) can each have N12. NodeComment is keyed by nodeId alone, and C1 `list_comments(nodeId)` and `add_comment(nodeId, ...)` carry no pack. Comments from one specialty would show on the other's node, and BR2.7 says comments span versions. | Make nodeId unique across packs (for example a pack-prefixed ID rule checked at load), or key comments by (pack, nodeId). State the choice and the contract change. | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/functional-spec.md > W1 and State Machine; entities.md > PackVersion constraints | `load_pack` is described as creating a `live` version, but only `create_version` supersedes the old live one. Loading a second file for an existing pack, or a repeated or lower version number, leaves two live versions or an undefined result, which breaks "exactly one live version per pack". `changeSummary` is required but `load_pack` does not set it. | State what `load_pack` does for a pack that already exists (refuse, or treat it as the next version and supersede). Set `changeSummary` for initial loads. Enforce increasing version numbers on load. | Resolved (reviewer) |
| R-06 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/functional-spec.md > W6; entities.md | The `changes` input of `create_version` (add, edit, remove nodes and edges, and any new sources) has no schema. U5 needs version history per pack (C9 and AC8.2.2), but C1 has only `live_version`; no list-versions operation is specified. | Define the change-set shape, and add a version-list operation with number, publishedAt, publishedBy and changeSummary. Record the contract additions. | Resolved (reviewer) |
| R-07 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/entities.md > Source; rules.md > BR1.1 | Source is globally unique and not tied to a pack or version, yet BR1.1 refers to "a Source not in the pack" and `sources(version)` is a contract operation. How sources are stored and scoped per version (and added by `create_version`) is undefined. | State the Source scope (per pack version, or global) and how `sources(version)` and BR1.1 resolve against it. | Resolved (reviewer) |
| R-08 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/entities.md > Node.content; rules.md | The rule that no run of more than 25 copied words may appear is a node constraint, but no BR enforces it, and nothing in W1 or W6 checks it. The project forbids copying guideline text verbatim, and BR3.5 only checks drug-field placeholders. | Add a rule saying what happens to this constraint: a load-time check (and how it detects copying without the source text), or an explicit content-review step with an owner. Extend the placeholder check beyond drug fields if intended. | Resolved (reviewer) |
| R-09 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/rules.md > BR2.4 and BR1.2 | "Most specific matching range" and "widest range" are not defined (ordering among sex, ageBand and pregnancy). BR1.2 requires edge conditions to reference "known" findings or tests without saying known to what set. | Give a precedence order and a width definition for ranges, and name the set that edge-condition references are checked against. | Resolved (reviewer) |
| R-10 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/entities.md > Node.content constraint | The attribute still lists "no run of more than 25 words copied" as a data constraint, but BR3.6 says U1 cannot detect copying at load. A reader may expect a load-time check. | Reword the constraint as an authoring-time rule enforced outside U1, referring to BR3.6. | New |
| R-11 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/rules.md > BR1.3 (create_version, load_pack numbering) | Two gaps. create_version does not say whether base must be the live version, so concurrent publishes could leave two children of one base. Numbers are major.minor, but "higher" is not stated as a numeric compare (1.10 versus 1.9). | State that base must equal the live version, otherwise refuse, and that version numbers compare numerically by major then minor. | New |
| R-12 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/functional-design/rules.md > BR2.2 and entities.md > Edge.edgeId | Condition-to-fact matching in BR2.2 does not say whether it uses the same lowercase, trim and synonym rule as BR2.1. edgeId has no stated uniqueness scope, while removeEdgeIds relies on it. | Say that condition names match by the BR2.1 name rule, and that edgeId is unique within a version and stable across versions. | New |

> R-01 Reviewer note: Fact, Step and the facts-taking neighbours and search are defined in entities.md, rules.md BR2.1-BR2.3 and C1. Status lives on Step, not Edge.

> R-02 Reviewer note: FieldSchema gives required keys per type, including symptom and drug synonyms. Unit handling is a fixed table per measure with examples (BR2.1). The table's full contents are left to Code Generation, which is acceptable.

> R-03 Reviewer note: U1 now owns match_claims and find_supporting_node (BR2.5). C1 lists both, and C6's check_line uses them.

> R-04 Reviewer note: Node and source IDs are pack-prefixed and globally unique, and the prefix is checked at load (BR1.2). Comments key on that ID (BR2.7).

> R-05 Reviewer note: W1 and BR1.3 define a re-load of an existing pack, the increasing-number rule, VersionNotIncreasing, and changeSummary.

> R-06 Reviewer note: ChangeSet is defined in entities.md, and list_versions is in W6, BR1.3 and C1.

> R-07 Reviewer note: Source belongs to a pack and carries into every version. sources(version) returns the ones that version's nodes cite.

> R-08 Reviewer note: Verbatim-copy checking moved to authoring (BR3.6). The placeholder check covers every field and content (BR3.5).

> R-09 Reviewer note: BR2.4 defines precedence, tie-break and widest. BR1.2 defines the known set for edge conditions as names of symptom, metric and test nodes.

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| None listed for this stage | Not run | Review was by reading and cross-checking against the C1 contract. C1 operations and Fact, Step and ChangeSet shapes agree with the functional design. |

### Summary

All nine prior findings are resolved: the C1 contract and the unit's design now agree on facts-aware traversal, claim matching ownership, pack-prefixed IDs, versioning and ChangeSet. Only minor wording and edge-case gaps remain, none of which blocks a developer from implementing.
