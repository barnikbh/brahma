# Entities — u1-knowledge-graph

Upstream: `unit-of-work.md` (U1), `components.md` (KnowledgeGraph entities), `contract-summary.md` (C1), `requirements.md` (FR1, FR2, FR3), `stories.md` (US3.2, US3.6, US8.2, US9.1).

```yaml
entities:
  - name: Pack
    description: A named body of clinical knowledge for one specialty (e.g. IBD, Urology stub).
    attributes:
      - { name: packId, type: identifier, required: true, unique: true }
      - { name: name, type: text, required: true, unique: true, constraints: "1-40 chars" }
      - { name: code, type: text, required: true, unique: true, constraints: "2-5 uppercase letters, the node and source ID prefix (e.g. IBD, URO)" }
      - { name: specialty, type: text, required: true }
      - { name: liveVersionNumber, type: version-string, required: false, constraints: "points to a PackVersion of this pack with status live" }
    relationships:
      - { to: PackVersion, cardinality: "1 to many", direction: "Pack has versions" }

  - name: PackVersion
    description: An immutable snapshot of a pack's nodes and edges.
    attributes:
      - { name: packVersionId, type: identifier, required: true, unique: true }
      - { name: packId, type: reference, references: Pack, required: true }
      - { name: number, type: version-string, required: true, constraints: "major.minor, unique within pack, increasing" }
      - { name: status, type: enum, allowed: [live, superseded], required: true }
      - { name: publishedAt, type: timestamp, required: true }
      - { name: publishedBy, type: reference, references: "Profile (u2-platform, id only)", required: true }
      - { name: changeSummary, type: text, required: true }
      - { name: basedOn, type: reference, references: PackVersion, required: false }
    constraints:
      - "Exactly one live version per pack."
      - "Once created, no attribute except status changes (live -> superseded)."
    relationships:
      - { to: Node, cardinality: "1 to many", direction: "version contains nodes" }
      - { to: Edge, cardinality: "1 to many", direction: "version contains edges" }

  - name: Node
    description: One clinical fact or decision point within a version.
    attributes:
      - { name: nodeId, type: identifier, required: true, constraints: "pack-prefixed and globally unique (e.g. IBD-N12, URO-N3); stable across versions of its pack; the prefix must equal the pack's code, checked at load" }
      - { name: packVersionId, type: reference, references: PackVersion, required: true }
      - { name: type, type: enum, required: true, allowed: [symptom, metric, diagnosis, subtype, test, treatment_tier, drug, monitoring, response_criterion, diet, watch_out, escalation, interaction, allergy_cross_reactivity] }
      - { name: label, type: text, required: true, constraints: "1-80 chars" }
      - { name: content, type: text, required: true, constraints: "paraphrased; no run of more than 25 words copied from a source" }
      - { name: fields, type: structured-map, required: true, constraints: "type-specific keys (see FieldSchema); values are what claims are checked against" }
      - { name: sourceIds, type: list-of-reference, references: Source, required: true, min: 1 }
      - { name: plausibleRange, type: structured, required: false, constraints: "metric only: {low, high, unit}" }
      - { name: referenceRanges, type: list-of-structured, required: false, constraints: "metric only: [{sex: female|male|any, ageBand?, pregnancy?, low?, high?, unit}]" }
      - { name: column, type: enum, required: true, allowed: [findings, diagnosis, tests, subtype, treatment, monitor] }
      - { name: alternative, type: boolean, default: false, constraints: "true for considered-but-not-taken branches such as infectious colitis" }

  - name: FieldSchema
    description: >
      The structured fields each node type carries (part of Node.fields). Every key listed without "?" is
      required for that type and checked at load (BR1.4).
    attributes:
      - { name: symptom, type: structured, constraints: "{name, synonyms: [..], durationMin?: {value, unit}}" }
      - { name: metric, type: structured, constraints: "{measure, unit (canonical), threshold?, comparator?: lt|le|gt|ge|eq}" }
      - { name: diagnosis, type: structured, constraints: "{name, code?}" }
      - { name: subtype, type: structured, constraints: "{name, extent?, severity?, code?}" }
      - { name: test, type: structured, constraints: "{name, resultOptions: [..]}" }
      - { name: treatment_tier, type: structured, constraints: "{tier: 1|2|3, entryCriteria, drugNodeIds: [..]}" }
      - { name: drug, type: structured, constraints: "{drug, synonyms: [..], drugClass, route, doseValue, doseUnit, doseBasis: absolute|per_kg, rounding, frequency, duration, contraindications: [..]}" }
      - { name: monitoring, type: structured, constraints: "{measure, unit, threshold, comparator, interval}" }
      - { name: response_criterion, type: structured, constraints: "{tier, measure, unit, threshold, comparator, verdict: responding|partial|not_responding}" }
      - { name: diet, type: structured, constraints: "{advice}" }
      - { name: watch_out, type: structured, constraints: "{sign, action}" }
      - { name: escalation, type: structured, constraints: "{trigger, action}" }
      - { name: interaction, type: structured, constraints: "{a: drug-or-class, b: drug-or-class, severity: major|moderate|minor}" }
      - { name: allergy_cross_reactivity, type: structured, constraints: "{allergenClass, conflictingDrugClasses: [..]}" }

  - name: Fact
    description: A finding or test result passed in by a caller to evaluate edge conditions (not stored by U1).
    attributes:
      - { name: kind, type: enum, allowed: [finding, test], required: true }
      - { name: name, type: text, required: true }
      - { name: value, type: "number or text", required: false }
      - { name: unit, type: text, required: false }

  - name: Step
    description: One result of neighbours (not stored).
    attributes:
      - { name: edge, type: Edge, required: true }
      - { name: node, type: Node, required: true }
      - { name: status, type: enum, allowed: [followable, not_taken, alternative, unknown_input], required: true }

  - name: ChangeSet
    description: The input to create_version (not stored as such).
    attributes:
      - { name: addNodes, type: list-of-Node, required: false }
      - { name: updateNodes, type: list-of-Node, required: false, constraints: "replaces the node with the same nodeId" }
      - { name: removeNodeIds, type: list-of-text, required: false }
      - { name: addEdges, type: list-of-Edge, required: false }
      - { name: removeEdgeIds, type: list-of-text, required: false }
      - { name: addSources, type: list-of-Source, required: false }
      - { name: changeSummary, type: text, required: true }

  - name: Edge
    description: A directed relation between two nodes of the same version.
    attributes:
      - { name: edgeId, type: identifier, required: true }
      - { name: packVersionId, type: reference, references: PackVersion, required: true }
      - { name: fromNodeId, type: reference, references: Node, required: true }
      - { name: toNodeId, type: reference, references: Node, required: true }
      - { name: relation, type: enum, required: true, allowed: [suggests, confirmed_by, refines_to, first_line, escalate_to, offers_drug, monitor_with, diet, watch_for, surgery_if, alternative_to, responds_if] }
      - { name: condition, type: structured, required: false, constraints: "{finding|test, comparator, value, unit} — edge is followable only if met" }
    constraints:
      - "No self-edges; both ends in the same version."

  - name: Source
    description: A cited guideline or paper. Sources belong to a pack and are carried into every version of it; sources(version) returns the ones that version's nodes cite.
    attributes:
      - { name: sourceId, type: identifier, required: true, unique: true, constraints: "pack-prefixed (e.g. IBD-S3)" }
      - { name: packId, type: reference, references: Pack, required: true }
      - { name: title, type: text, required: true }
      - { name: year, type: integer, required: true, min: 1990, max: 2026 }
      - { name: section, type: text, required: true, constraints: "section or page" }
      - { name: url, type: url, required: false }

  - name: NodeComment
    description: A comment on a node (any version of it, by its globally unique, pack-prefixed nodeId).
    attributes:
      - { name: commentId, type: identifier, required: true }
      - { name: nodeId, type: text, required: true, constraints: "pack-prefixed, so comments never cross packs" }
      - { name: authorProfileId, type: reference, references: "Profile (u2-platform, id only)", required: true }
      - { name: text, type: text, required: true, constraints: "1-1000 chars" }
      - { name: createdAt, type: timestamp, required: true }
```

## Summary

Seven stored entities plus three call shapes (**Fact**, **Step**, **ChangeSet**) used by U1's operations. Node and source IDs are pack-prefixed and globally unique. **Pack** groups knowledge for a specialty. **PackVersion** is the immutable snapshot every read names. **Node** and **Edge** form the graph, with the structured fields (FieldSchema) that the grounding check matches claims against. **Source** gives every node its citation. **NodeComment** holds doctors' comments. Profile IDs are stored as plain identifiers: U1 never imports U2.
