# Feasibility Assessment — Clinical Decision Graph

Upstream: `ideation/intent-capture/intent-statement.md` (problem, user, success metrics, product boundary). Answers referenced as Q1–Q10 are in `feasibility-questions.md`.

## Verdict

**Feasible with conditions.** The initiative is technically viable for one builder by Nov 4, 2026, 9:00 PM ET, provided three conditions hold:

1. Meta Model API access is obtained before any agent work starts (Q2). Without it nothing that talks to a model can be built or demoed.
2. The weekend of Oct 31 – Nov 1 adds real hours on top of evenings (Q6, Q10). Evenings alone (about 12 hours) do not cover the committed scope.
3. The cut order is followed if time runs short: the update layer drops to its minimum form first (Q8).

## Effort Budget (conservative)

| Item | Estimate | Basis |
|------|----------|-------|
| Evening hours, Oct 29 – Nov 4 | ~12 h | About 2 h a day over 6 evenings (Q6) |
| Weekend hours, Oct 31 – Nov 1 | Unknown | You said you'd add them (Q10) but not how many; see Assumptions |
| Committed deliverables | 5 components + a deployed URL + a demo video + a 20-case benchmark (Q7, Q9, intent statement) | intent-statement.md, Initial Scope Signal |

A conservative planning figure is 12 evening hours plus whatever the weekend gives. Until the weekend hours are known, plan the must-haves to fit inside the evening hours alone.

## Technical Viability by Component

| Component | Viability | Main risk | Minimum acceptable form |
|-----------|-----------|-----------|--------------------------|
| Clinical knowledge graph (IBD) | High: content comes from published guidelines and literature you select, paraphrased and cited per node (Q5) | Authoring the IBD pathway with citations takes longer than coding; the content reviewer's timing is unknown (intent statement) | The demo-case pathway fully filled in (symptoms and metrics → diagnosis → confirmatory tests → sub-type → treatment tiers → monitoring, diet, escalation), with every node cited |
| Agent that searches and walks the graph | Medium: depends entirely on Meta Model API access (Q2) | Access delay; the model answering beyond the graph | Answers only from the nodes it walked, citing each one |
| Session audit with explanations | High: it records what the agent already does | Low | Per-session record of the question, the nodes walked, sources cited and the answer |
| Doctor chat with a graph canvas | Medium: the visual design is yours and still to come (intent review, R-03) | Polishing the UI is easy to over-spend on | Chat plus a view highlighting the graph region used in the session |
| Knowledge update layer | Medium | Lowest priority by your choice (Q8) | A doctor links a source and sees a new version with a comment; the background updater is a scheduled stub (Q8) |
| Synthetic benchmark | High once the agent works | Writing 20 good synthetic cases takes time (Q9) | 20 synthetic IBD cases; pass = at least 95% of recommendations trace to a graph node and source, compared with the same model with no graph (Q9) |
| Deployed URL plus demo video | Medium | Deploy-day surprises; hosting not yet chosen | A public URL judges can try, plus a short recorded walkthrough (Q7) |

## Skill and Stack Fit

You'll build with Python for the backend and agent and TypeScript/React for the web app (Q1). That is a common pairing for this kind of build, so it adds no feasibility risk beyond the time budget.

## Regulatory and Compliance View

- Synthetic data only, so no real patient health information is processed and HIPAA is out of scope for this version (Q4; intent statement).
- The audit trail and access control are designed so a later HIPAA-scoped version is plausible, without claiming any certification (Q4).
- Every screen and answer carries a "decision support, not diagnosis" disclaimer (Q4; intent statement).
- Guideline text is generally copyrighted, so graph nodes paraphrase and cite their sources rather than copying (Q5).

## Risk Summary

The top risks are API access (Q2), the time budget (Q6, Q10) and content-authoring effort (Q5). The RAID log (`raid-log.md`) tracks them with owners and mitigations.

## Assumptions & Open Questions

- [assumption] The weekend adds enough hours (planning guess: 8–12) to cover the canvas polish, deployment, the video and the benchmark; the actual number is not stated (Q10).
- [assumption] Meta Model API access can be obtained by Oct 30 (Q2).
- Open question: whether open-weights credits will be used at all (Q3).
