# Scope Definition — Questions

Already settled upstream, so not asked again: all five components ship in some form; synthetic data and IBD content only; the update layer drops to its minimum first; the benchmark is 20 cases at a 95% bar; delivered as a deployed URL plus video (intent-statement.md, feasibility-assessment.md, constraint-register.md).

## Q1. [Product] Second in the cut order

The update layer shrinks first. If time is still short after that, what shrinks next?

A. The benchmark: fewer than 20 cases, same 95% bar
B. Canvas interaction: a static highlighted view instead of an explorable one
C. The audit explanation view: the session log stays, the rich "why" view goes
D. Nothing else: everything else stays at its full form
X. Other (please specify)

[Answer]: D

## Q2. [Product] Build order

With about 12 evening hours plus weekend time, the order matters. Which comes first?

A. Risk first: a thin end-to-end slice (Meta API call → agent walks a tiny IBD graph → answer with citations → shown in the app → deployed), then fill in content and polish
B. Content first: author the full IBD pathway, then build the agent and app around it
C. UI first: build the app from your visual design, then wire in the agent and graph
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q3. [Product] Internal milestones

Are there dates you want to hold yourself to before the Nov 4, 9:00 PM ET deadline?

A. Thin slice deployed by Oct 31; feature-complete by Nov 2; video and submission on Nov 3–4
B. Feature-complete by Nov 3; video and submission on Nov 4
C. No internal milestones, just the final deadline
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. [Clinical] How deep the demo case goes

The demo walks one synthetic IBD patient end to end. How far does the diagnosis branch go?

A. Ulcerative colitis only, refined to extent and severity (e.g. pancolitis, severe), then its treatment tiers, monitoring, diet and surgery triggers
B. Both ulcerative colitis and Crohn's disease branches, each refined to sub-type
C. Start from a known ulcerative colitis diagnosis and cover only the treatment ladder and monitoring
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q5. [Product] Showing it generalises beyond IBD

The knowledge model must work for oncology, urology and others, but only IBD is filled in. How should judges see that?

A. A tiny second-specialty stub (a handful of nodes, e.g. urology) loaded through the same model
B. Explained in the video and the write-up only
C. Not needed for the submission
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. [Product] Doctor sign-in

Feasibility kept access control "designed for later". What does the first version need?

A. No sign-in: one demo doctor, so judges go straight in
B. Simple sign-in with seeded demo accounts, so audit records name a doctor
C. A demo doctor by default, with audit records still tagged to that doctor's identity
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q7. [Product] Follow-up: content first vs. the Oct 31 slice

Three answers pull against each other. Content goes first (Q2) and now covers both ulcerative colitis and Crohn's (Q4), roughly doubling the authoring. Meanwhile a deployed thin slice is due Oct 31 (Q3), and Meta API access isn't set up yet (feasibility risk R1). Content first means a late API problem would only surface around Oct 31. How should these fit?

A. Content first, but do one Meta API test call on day one, before authoring, to retire the access risk
B. Content first, but author the ulcerative colitis branch fully first and Crohn's second, so the Oct 31 slice runs on UC alone
C. Both A and B
D. Keep it as is: full content for both branches first, then everything else
X. Other (please specify)

[Answer]: B

## Consolidated Summary Confirmation

- Cut order: only the update layer shrinks (to source-link plus versioned, commented changes, with the background updater as a stub); every other component stays at its full form (Q1)
- Build order: content first, starting with the ulcerative colitis branch fully authored, then the Crohn's disease branch (Q2, Q7)
- Demo case depth: both UC and Crohn's branches, each refined to sub-type, with their treatment tiers, monitoring, diet and surgery triggers (Q4)
- Milestones: a thin slice deployed by Oct 31 (running on the UC branch); feature-complete by Nov 2; video and submission on Nov 3–4, before 9:00 PM ET (Q3, Q7)
- Generality: a tiny second-specialty stub (e.g. a handful of urology nodes) loaded through the same knowledge model (Q5)
- Sign-in: simple sign-in with seeded demo accounts, so every audit record names a doctor (Q6)
- Meta API access stays a separate risk: it isn't tested before content authoring starts (Q7)

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
