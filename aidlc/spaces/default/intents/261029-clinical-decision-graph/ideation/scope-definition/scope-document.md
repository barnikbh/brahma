# Scope Document — Clinical Decision Graph

Upstream: `ideation/intent-capture/intent-statement.md` (problem, user, success metrics, product boundary), `ideation/feasibility/feasibility-assessment.md` (verdict, minimum forms, effort budget) and `ideation/feasibility/constraint-register.md` (C-T*, C-O*, C-R*, C-Q*). Answers Q1–Q7 are in `scope-definition-questions.md`.

## Scope Statement

A decision-support tool for a specialist working up and treating inflammatory bowel disease (IBD). It walks one synthetic patient from symptoms and metrics to a precise diagnosis and a tiered treatment plan, and grounds every step in a cited, versioned clinical knowledge layer. Each session is audited and explained. (intent-statement.md; Q4)

## In Scope (first version, due Nov 4, 2026, 9:00 PM ET)

| Capability | First-version form | Source |
|------------|--------------------|--------|
| Clinical knowledge model | One general model of the decision layer (symptoms, metrics, diagnoses and sub-types, confirmatory diagnostics, treatment tiers, monitoring metrics, diet, watch-outs, escalation triggers such as surgery, sources, versions), usable for any specialty | intent-statement.md; C-T4 |
| IBD content: ulcerative colitis | The full branch, refined to sub-type (e.g. extent and severity), with treatment tiers, monitoring, diet and surgery triggers, every node cited from published guidelines and literature | Q4, Q7; C-R4 |
| IBD content: Crohn's disease | The same depth as ulcerative colitis, authored second | Q4, Q7 |
| Second-specialty stub | A handful of nodes in another specialty (e.g. urology) loaded through the same model, to show it generalises | Q5 |
| Grounded agent | Answers by searching and walking the knowledge layer only, citing every node and source it used | intent-statement.md; C-T3 |
| Session audit and explanation | Every session recorded with the question, the path walked, the sources cited and the answer, plus an explanation view | Q1 (stays at full form) |
| Doctor app | Simple sign-in with seeded demo accounts; chat; a canvas of the knowledge-graph region used in the session; built from your visual design | Q6, Q1; C-O6 |
| Knowledge update layer (minimum form) | A doctor links a source or submits a change and sees a new version with a comment; the silent background updater is a scheduled stub | Q1; feasibility-assessment.md |
| Synthetic benchmark | About 20 synthetic IBD cases; pass = at least 95% of recommendations trace to a node and source, compared with the same model with no knowledge graph | C-Q2 |
| Disclaimers | "Decision support, not diagnosis" on every answer and screen | C-R2 |
| Delivery | A deployed public URL plus a demo video | C-T5 |

## Out of Scope (first version)

| Item | Why | Source |
|------|-----|--------|
| Real patient data and EHR integration | Synthetic or de-identified data only | intent-statement.md; C-R1 |
| Full content for any specialty other than IBD | Only a small stub shows the model generalises | intent-statement.md; Q5 |
| A fully working silent background updater | Kept as a scheduled stub; first to shrink | Q1; feasibility-assessment.md |
| HIPAA scope or any certification | Synthetic data only; audit and access are designed so a later HIPAA-scoped version is plausible | C-R3 |
| Open sign-up or real doctor accounts | Seeded demo accounts only | Q6 |

## Cut Order

Only the update layer shrinks, to its minimum form above. Everything else stays at its full first-version form. (Q1)

## Milestones

| Date | Milestone | Source |
|------|-----------|--------|
| Oct 29 – 30 | Knowledge model plus the ulcerative colitis branch authored and cited | Q2, Q7 |
| Oct 31 | Thin slice deployed, running on the ulcerative colitis branch | Q3, Q7 |
| Nov 2 | Feature-complete: Crohn's branch, second-specialty stub, full audit and app, minimum update layer, benchmark | Q3 |
| Nov 3 – 4 | Demo video and submission, before 9:00 PM ET | Q3; C-O1 |

## Scope-vs-Timeline Check

- Capacity is evenings (~2 h/day) plus weekend hours on Oct 31 – Nov 1 (C-O3). Adding the Crohn's branch (Q4) roughly doubles authoring, and nothing but the update layer may shrink (Q1). The schedule has no slack. (feasibility-assessment.md, Effort Budget)
- Content comes before the thin slice (Q2), and Meta API access isn't tested first (Q7). If access fails, that surfaces only around the Oct 31 slice. (feasibility-assessment.md, condition 1)

## Assumptions & Open Questions

- [assumption] The 20 benchmark cases span both ulcerative colitis and Crohn's disease, since the demo now covers both.
- [assumption] Weekend hours are enough to hit the Oct 31 slice and the Nov 2 feature-complete date with no cut beyond the update layer.
- Open: if the Oct 31 slice is missed, should anything beyond the update layer be cut, despite Q1? This needs a decision at that point.
