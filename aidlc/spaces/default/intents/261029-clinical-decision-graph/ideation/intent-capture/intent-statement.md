# Intent Statement — Clinical Decision Graph

## Problem Statement

When a specialist works up a patient, they move from what they hear and measure (for example, frequent bloody stool for six months, low hemoglobin, high stool calprotectin) to a working diagnosis, then order further diagnostics to confirm it and narrow it to a precise sub-type, and finally choose a tiered treatment plan with metrics to watch, diet, and escalation triggers such as surgery. [desc] [Q1]

This pathway mostly lives in the experienced doctor's head and is built from years of practice. The problem this initiative solves is making that tacit pathway explicit and walkable, so each step from symptoms to monitoring can be followed and checked. [Q1]

General-purpose AI assistants can't be trusted for this today because they can state things with no source. The tool must answer only from a curated clinical decision layer, so every output can be audited back to where it came from. [desc]

The tool is decision support for the doctor, not a diagnosis. [desc]

## Target Customer

- A medical specialist, with a gastroenterologist working up and treating inflammatory bowel disease (IBD) as the first example. [Q2] [desc]
- They use it both live during a consultation and before or after one, for case preparation and follow-up review. [Q3]
- What they gain: their decision pathway (diagnosis, refinement, tiered treatment, monitoring, diet, watch-outs) is laid out in front of them, with each step traceable to its source, and they can add to or correct the knowledge themselves. [Q1] [desc]

## Success Metrics

| Metric | Target | Source |
|--------|--------|--------|
| End-to-end demo case | One synthetic IBD patient walked from symptoms and metrics to a precise sub-type, a treatment tier and a monitoring plan | [Q4] |
| Ungrounded claims in the demo case | Zero: every recommendation traces to a knowledge-graph entry and its source | [Q4] |
| Benchmark against a plain AI model | A set of synthetic cases scored for grounded-answer rate, the tool against the same model with no knowledge graph | [Q4] |
| Submission | Submitted by Nov 4, 2026, 9:00 PM ET | [desc] |

## Initiative Trigger

- The Meta Global AI Developer Hackathon, Theme 2 "Build for Your World", with submissions due Nov 4, 2026 at 9:00 PM ET. [desc]
- A firsthand connection: a close family member or friend is a doctor or a patient, which is where the problem comes from. [Q6]
- Entered in the Indie track. [Q9]

## Initial Scope Signal

- Workflow-selected scope: `mvp` (workflow-selected). [scope]
- User-confirmed product boundary for the first version: [Q5]
  - In: all five components in some form: the clinical knowledge graph, the agent that answers by searching and walking it, the per-session audit trail with explanations, the doctor-facing chat with a canvas showing the graph region in use, and the knowledge update layer (background updates plus doctor-submitted updates and sources, with versions and comments). [Q5] [desc]
  - Out: real patient data and EHR integration (synthetic or de-identified cases only). [Q5] [desc]
  - Out: clinical content beyond IBD; the knowledge model stays general enough for oncology, urology and other fields, but only IBD is filled in. [Q5] [desc]

## Assumptions & Open Questions

- [assumption] The benchmark has no numeric target yet (how many synthetic cases, and what grounded-answer rate counts as a win); it needs one before requirements are written.
- [assumption] The family member or friend who will review the IBD pathway content is available to do so before Nov 4; their review window is not yet known.
