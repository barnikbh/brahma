# Feasibility & Constraints — Questions

Context: one builder, about six days to Nov 4, 9:00 PM ET; all five components ship in some form; synthetic data and IBD content only (intent-statement.md).

## Q1. [Developer] Your strongest stack for a six-day build

Feasibility hinges on building in what you already know well. Which fits you best?

A. Python for the backend and agent, TypeScript/React for the web app
B. TypeScript end to end
C. Python only, including a Python-based UI
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. [Developer] Access to the Meta Model API

Using Meta's models is a hackathon requirement, and the whole agent depends on it. Where are you with access?

A. I have an API key and have made a test call
B. I'm registered but haven't tested it yet
C. Not yet
D. Not sure what access is offered
X. Other (please specify)

[Answer]: C

## Q3. [Developer] Open-weights model credits

Some participants get $100 credits from Baseten, Modal or Fireworks for Meta's open-weights models (useful for the benchmark or embeddings). Do you have them?

A. Yes, I have credits
B. I've applied or can claim them
C. Not needed: I'll use the Meta Model API only
D. Not yet defined
X. Other (please specify)

[Answer]: D

## Q4. [Compliance] Regulatory stance for the first version

With synthetic data only, no real patient health information is handled. How should we treat health-data rules?

A. Treat it as a no-patient-data demo: no HIPAA scope, but clear "decision support, not diagnosis" disclaimers everywhere
B. Same as A, and also design the audit trail and access control so a later HIPAA-scoped version is plausible (no certification claimed)
C. Not applicable
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q5. [Clinical] Where the IBD knowledge comes from

The graph has to be filled from sources that can be cited per node. What will you draw on? (Guideline text is usually copyrighted, so nodes would paraphrase and cite rather than copy.)

A. Published guidelines and open literature (e.g. ACG, AGA, ECCO) that I select
B. My reviewer's own pathway knowledge, written down
C. Both: guidelines as the citable base, the reviewer's pathway layered on top
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. [Product] Your time budget until Nov 4

This decides how much of each component can be real. How much time can you put in?

A. Full-time, 8+ hours a day
B. Part-time, about 3-5 hours a day
C. Evenings only, about 2 hours a day
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q7. [Product] How judges will see it

Indie judging asks whether it works. How will the submission be shown?

A. A deployed public URL judges can try, plus a demo video
B. A demo video of a local run only
C. A deployed URL only
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q8. [Product] What gets reduced first if time runs short

All five components ship "in some form" (the review flagged this as undefined). You own the app's visual design. If time runs short, which component drops to its minimum form first?

A. The update layer: a doctor can link a source and see a new version with a comment, but the silent background updater is only a scheduled stub
B. The audit layer: a per-session log with the path walked, but no rich explanation view
C. The canvas: a static view of the graph region used, with no interaction
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q9. [Product] The synthetic benchmark's target

You asked for a synthetic benchmark (review finding R-02). It needs a size and a pass mark so it can pass or fail. Which target?

A. About 20 synthetic IBD cases; win = at least 95% of the tool's recommendations trace to a graph node and source, against the same model with no graph
B. About 50 synthetic cases with the same 95% bar
C. About 10 cases, scored by your reviewer as well as automatically
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q10. [Product] Follow-up: time against scope

Evenings only (Q6) gives roughly 12 hours of building before Nov 4. Against that, the first version promises all five components, a deployed URL and video (Q7), a benchmark (Q9), a polished UI, and Meta API access that isn't set up yet (Q2). That is a real squeeze. How do you want to resolve it?

A. Add time: I'll put in extra hours on the weekend (Oct 31 – Nov 1) on top of evenings
B. Keep the time, cut harder: the demo case is the must-have; the benchmark, update layer and canvas interaction are stretch goals
C. Both: add weekend time and treat the benchmark and update layer as stretch goals
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

- Stack: Python for the backend and agent, TypeScript/React for the web app (Q1)
- Meta Model API: no access yet; getting it is the first dependency (Q2)
- Open-weights credits: undecided (Q3)
- Compliance: synthetic-only demo with no HIPAA scope and disclaimers everywhere, with the audit trail and access control designed so a later HIPAA-scoped version is plausible; no certification claimed (Q4)
- IBD knowledge: published guidelines and open literature you select, paraphrased and cited per node (Q5)
- Time: evenings (~2h/day) plus extra weekend hours on Oct 31 – Nov 1 (Q6, Q10)
- Delivery: a deployed public URL plus a demo video (Q7)
- First to drop to minimum if time runs short: the update layer (doctor links a source and sees a versioned, commented change; the background updater is a scheduled stub) (Q8)
- Benchmark: about 20 synthetic IBD cases; win = at least 95% of recommendations trace to a graph node and source, against the same model with no graph (Q9)

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
