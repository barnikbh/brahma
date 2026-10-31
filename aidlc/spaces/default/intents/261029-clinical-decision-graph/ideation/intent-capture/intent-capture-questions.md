# Intent Capture & Framing — Questions

## Sources

- [desc] Initial description: "Build a decision-support tool for doctors (Meta Global AI Developer Hackathon, Theme 2 \"Build for Your World\", due Nov 4 2026 9:00 PM ET; must use Meta Model API models such as Muse Spark; synthetic or de-identified data only; decision support, not diagnosis). Components: (1) a knowledge graph encoding the latest clinical decision layer across medical specialties - symptoms, metrics/lab values, diagnoses and their sub-types, additional diagnostics needed to confirm and refine a diagnosis, tiered treatment plans (e.g. IBD: mesalamine, then steroids, then biologics such as Stelara or Remicade), metrics to monitor, diet, physiotherapy and other modalities, watch-outs and escalation triggers such as surgery - so the LLM is grounded and does not hallucinate; (2) an agentic layer (LangGraph or similar, using the hackathon LLM APIs) that answers by search and traversal over the graph so every output is auditable; (3) an audit layer that audits each session with built-in explainability; (4) an application layer where doctors chat with the agent alongside a canvas view of the knowledge-graph region used in the session, with a polished UI (design drafts to come); (5) an update layer: a silent background process that updates the graph, plus UI for a doctor to submit an update or link a new source which the agent then ingests, with versioning of the knowledge layer and comments. Example domain: gastroenterology / IBD, but the model must generalise to oncology, urology and other fields. Plan properly first; do not start building yet."
- [scope] Workflow-selected scope: `mvp`.

## Q1. [Product] The headline problem

All five components serve one story for the judges. Which problem should the first version prove above all?

A. Tacit expertise: the experienced doctor's pathway (symptoms and metrics → working diagnosis → confirmatory tests → precise sub-type → tiered treatment → monitoring) is made explicit and walkable
B. Trust: LLM answers are grounded only in a curated graph, so every claim traces to a node and a source and nothing is hallucinated
C. Time: a doctor gets to the next test or next treatment step faster than by searching guidelines
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. [Product] Primary user

Who is the doctor this first version is built for? This decides the depth of the graph and the tone of the agent.

A. A specialist (e.g. a gastroenterologist) refining a diagnosis and stepping through treatment tiers
B. A GP or primary-care doctor deciding which workup to order and when to refer
C. A resident or junior doctor who doesn't yet carry the senior doctor's pathway in their head
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. [Product] Moment of use

When does the doctor open the tool? This shapes speed and how much text the agent writes.

A. Live, during the consultation
B. Before or after the consultation (case preparation, follow-up review)
C. Both
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q4. [Product] What success looks like on Nov 4

How should we measure that the first version worked?

A. A demo case: one synthetic IBD patient end to end (symptoms → sub-type → treatment tier → monitoring), with every recommendation traced to graph nodes and sources and zero ungrounded claims
B. A benchmark: a set of synthetic cases scored for grounded-answer rate against a plain LLM with no graph
C. Both A and B
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q5. [Product] What the first version leaves out (select all that apply)

The plan is already set as an MVP. Which of these stay out of the version you submit on Nov 4?

A. Real patient data and EHR integration (synthetic cases only)
B. Clinical content beyond IBD (the graph model is general, but only IBD is filled in)
C. A fully automatic background updater (updates happen only when a doctor submits a change or links a source)
D. None: all five components ship in some form
X. Other (please specify)

[Answer]: A, B, D (read together: synthetic cases only and IBD content only, while all five components, including the background updater, ship in some form)

## Q6. [Clinical] Your firsthand connection

Theme 2 asks for a problem you know firsthand, and judges will want to hear it. What is your connection to this problem?

A. I'm a clinician myself
B. A close family member or friend is a doctor, or a patient with a condition like IBD
C. I've worked in health tech or with clinicians professionally
D. Not applicable / prefer not to say
X. Other (please specify)

[Answer]: B

## Q7. [Clinical] Who vouches for the medical content

The graph is only as trustworthy as its content. Who confirms the IBD pathway in it is right?

A. I do, from my own clinical knowledge
B. A doctor I can reach this week reviews it
C. Published guidelines only (e.g. ACG / ECCO), cited per node, with no human reviewer
D. Not yet defined
X. Other (please specify)

[Answer]: D

## Q8. [Team] Team and who decides

Who is building this, and who makes scope and priority calls? (Also: anyone you need to keep updated as you go?)

A. Just me: I decide everything, no one to update
B. A small team (2-4); I make the final scope calls
C. A small team that decides together
D. Not identified
X. Other (please specify)

[Answer]: A

## Q9. [Team] Hackathon track

The two tracks are judged differently: Indie on creativity, technical ambition and whether it works; Startup on technical execution and whether it holds up in production. Which are you entering?

A. Indie
B. Startup
C. Not decided yet
D. Not applicable
X. Other (please specify)

[Answer]: A

## Q10. [Clinical] Follow-up: a clinical sounding board

You left the content reviewer open (Q7) and your connection is through a family member or friend (Q6). Since the headline is the doctor's tacit pathway, could that person look over the IBD pathway or the demo before Nov 4?

A. Yes, they can review the IBD pathway content
B. Yes, but only a quick look at the finished demo
C. No; rely on published guidelines cited per node
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

- Headline problem: make the experienced doctor's tacit pathway (symptoms and metrics → working diagnosis → confirmatory tests → precise sub-type → tiered treatment → monitoring) explicit and walkable (Q1)
- Primary user: a specialist, e.g. a gastroenterologist (Q2)
- Used both live in the consultation and before/after it (Q3)
- Success on Nov 4: a fully traced synthetic IBD demo case with zero ungrounded claims, plus a benchmark of synthetic cases scored for grounded-answer rate against a plain LLM (Q4)
- Out of v1: real patient data / EHR (synthetic only) and non-IBD content; all five components still ship in some form, including the background updater (Q5)
- Firsthand connection: a close family member or friend who is a doctor or a patient (Q6)
- Content reviewer: that person reviews the IBD pathway content (Q7, Q10)
- Team: just you; you decide everything, no one to update (Q8)
- Track: Indie (Q9)

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct

## Assumption Confirmation

The intent statement and stakeholder map carry these open items:

- [assumption] The benchmark has no numeric target yet (how many synthetic cases, and what grounded-answer rate counts as a win); it needs one before requirements are written.
- [assumption] The family member or friend who will review the IBD pathway content is available to do so before Nov 4; their review window is not yet known.
- [assumption] When the content reviewer can look at the IBD pathway, and in what form (graph view, document, or demo), is not yet agreed.

A. Accept assumptions
B. Convert to follow-up questions

[Answer]: A. Accept assumptions
