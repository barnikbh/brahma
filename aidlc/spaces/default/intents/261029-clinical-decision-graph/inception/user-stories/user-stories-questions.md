# User Stories — Story Plan and Questions

## Story Plan

- **Personas (proposed):** Dr. Maya, consultant gastroenterologist (primary); demo urologist (second specialty); clinical reviewer (publishes knowledge changes); hackathon judge (watches the video, reads the benchmark, may run it locally). Source: `requirements.md` FR11.1, FR13; `intent-statement.md`.
- **Format:** "As a [persona], I want [goal], so that [benefit]", INVEST-checked, with Given/When/Then acceptance criteria (inception guardrails), IDs `US{group}.{seq}` and `AC{group}.{seq}.{n}`.
- **Priority:** MoSCoW taken from the requirements' priority table and cut order (`requirements.md`, Priority and Cut Order): FR7 prescription and FR8 follow-up are Could and cut first.
- **Traceability:** every FR and NFR maps to at least one story, or is marked Deferred to a named later stage (for example NFR5 secrets → code generation), in `traceability.json`.

## Q1. [Stories] How stories are grouped

How should the stories be grouped?

A. By the doctor's workflow: sign in → patients → consult walk → treatment → prescribe → follow up → audit → knowledge → benchmark (matches the demo video's order)
B. By component: knowledge, agent, audit, app, update layer (matches the five components in your original idea)
C. By persona: everything Dr. Maya does, then the reviewer, then the judge
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. [Stories] Story size

How small should each story be?

A. One screen state or one agent behaviour per story (about 35–45 stories), each buildable in one evening session
B. One screen per story (about 15–20 stories), with the states as acceptance criteria
C. One epic per requirement group (16 stories), with details as acceptance criteria
D. Not yet defined
X. Other (please specify)

[Answer]: X ("let's not go into these complications. This is a hackthon. let's go easy here with these." Read as: keep it light, about 15 to 20 stories, one per screen or agent capability, with short acceptance criteria)

## Q3. [Personas] The judge as a persona

Should the hackathon judge be a persona with their own stories (watching the demo, reading the benchmark, running it locally from the README)?

A. Yes: the judge gets stories for the benchmark page, the README setup and the demo walk as seen in the video
B. No: cover the benchmark and README as requirements only, with no judge persona
C. Yes, but only for the benchmark page
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Consolidated Summary Confirmation

- Stories follow the doctor's workflow, in the demo video's order: sign in → patients → consult walk → treatment → prescribe → follow up → audit → knowledge → benchmark (Q1)
- Kept light for the hackathon: about 15 to 20 stories, one per screen or agent capability, each with a few short Given/When/Then acceptance criteria (Q2)
- Three personas: Dr. Maya (gastroenterologist, primary), the demo urologist, and the clinical reviewer; no judge persona, so the benchmark (FR13) and the repo setup (FR16) stay as requirements only, with no stories (Q3)
- Priorities follow the approved requirements: prescription and follow-up are Could and cut first

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
