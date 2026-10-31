# Constraint Register — Clinical Decision Graph

Upstream: `ideation/intent-capture/intent-statement.md`. Answers Q1–Q10 are in `feasibility-questions.md`.

## Technical Constraints

| ID | Constraint | Type | Source |
|----|------------|------|--------|
| C-T1 | Must use Meta's models through the Meta Model API (Muse Spark series and related); open-weights Meta models are optional | Hackathon mandate | Project description; Q2, Q3 |
| C-T2 | Builder's stack: Python backend and agent, TypeScript/React web app | Skill fit | Q1 |
| C-T3 | Every agent answer must come only from the knowledge graph and cite the nodes and sources it used | Product principle | intent-statement.md, Problem Statement |
| C-T4 | The knowledge model must generalise to other specialties (oncology, urology, others) even though only IBD is filled in | Product boundary | intent-statement.md, Initial Scope Signal |
| C-T5 | Delivered as a deployed public URL plus a demo video | Delivery | Q7 |

## Organisational Constraints

| ID | Constraint | Type | Source |
|----|------------|------|--------|
| C-O1 | Submission due Nov 4, 2026, 9:00 PM ET | Deadline | intent-statement.md, Initiative Trigger |
| C-O2 | One builder, who makes every scope and priority decision | Team | intent-statement.md (stakeholders) |
| C-O3 | Time budget: evenings (~2 h/day) plus extra weekend hours Oct 31 – Nov 1 | Capacity | Q6, Q10 |
| C-O4 | Cut order: the update layer drops to its minimum form first | Priority | Q8 |
| C-O5 | Indie track: judged on creativity, technical ambition and whether it works | Evaluation | intent-statement.md, Initiative Trigger |
| C-O6 | The application's visual design comes from you and is still to be delivered | Dependency on builder | Intent review, R-03 |

## Regulatory Constraints

| ID | Constraint | Type | Source |
|----|------------|------|--------|
| C-R1 | Synthetic or de-identified data only; no real patient data or EHR integration | Data | intent-statement.md, Initial Scope Signal; Q4 |
| C-R2 | Positioned as decision support, not diagnosis, with disclaimers on every answer and screen | Medical-device positioning | intent-statement.md; Q4 |
| C-R3 | No HIPAA scope now; the audit trail and access control are designed so a later HIPAA-scoped version is plausible, with no certification claimed | Health data | Q4 |
| C-R4 | Guideline content is paraphrased and cited, not copied verbatim | Copyright | Q5 |

## Quality Constraints

| ID | Constraint | Type | Source |
|----|------------|------|--------|
| C-Q1 | Demo case: zero ungrounded claims | Success metric | intent-statement.md, Success Metrics |
| C-Q2 | Benchmark: about 20 synthetic IBD cases; pass = at least 95% of recommendations trace to a graph node and source, compared with the same model with no graph | Success metric | Q9 |

## Assumptions & Open Questions

- [assumption] C-O3's weekend hours are enough to cover the deployed URL, the video and the benchmark; the hour count is not stated.
