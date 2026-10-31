# RAID Log — Clinical Decision Graph

Upstream: `ideation/intent-capture/intent-statement.md`. Answers Q1–Q10 are in `feasibility-questions.md`. Owner is you (sole builder) unless noted.

## Risks

| ID | Risk | Likelihood | Impact | Mitigation | Source |
|----|------|-----------|--------|-----------|--------|
| R1 | Meta Model API access arrives late, blocking the agent, benchmark and demo | Medium | High | Apply today; make the first build task a test call; keep the agent's model interface swappable so building can start against a stand-in and switch to Meta's models before the demo | Q2 |
| R2 | Not enough hours: evenings plus an unknown amount of weekend time against the full scope | High | High | Plan the must-haves to fit the evening hours alone; follow the cut order (update layer first) | Q6, Q10, Q8 |
| R3 | Authoring and citing the IBD pathway takes longer than expected | Medium | High | Fill only the demo case's pathway first; widen coverage only for the benchmark cases | Q5 |
| R4 | The agent states something not in the graph, breaking the zero-ungrounded-claims promise | Medium | High | Answers may only cite nodes the agent walked; the benchmark measures this | intent-statement.md; Q9 |
| R5 | UI polish eats the remaining time | Medium | Medium | Your visual design fixes the target; build the canvas from it, not from scratch | Intent review, R-03 |
| R6 | Deploy-day failure means judges can't try the URL | Medium | Medium | Deploy a skeleton early (by Nov 1) and redeploy often; record the video before the final deploy | Q7 |
| R7 | The content reviewer isn't available in time to check the IBD pathway | Low | Medium | Share the pathway as soon as the demo case is filled in | intent-statement.md, Assumptions |

## Assumptions

| ID | Assumption | Validate by | Source |
|----|-----------|------------|--------|
| A1 | Meta Model API access can be obtained by Oct 30 | Test call succeeds | Q2 |
| A2 | Weekend hours (planning guess 8–12) cover the deployment, the video and the benchmark | You confirm the hours by Oct 31 | Q10 |
| A3 | Published guidelines and open literature are enough to cite every node in the IBD pathway | Demo-case pathway fully cited | Q5 |
| A4 | Your reviewer can look at the IBD pathway before Nov 4; window and format not yet agreed | Review session booked | intent-statement.md, Assumptions |
| A5 | The benchmark target (20 cases, 95% grounded) is reachable once the agent is grounded | First benchmark run | Q9 |

## Issues

| ID | Issue | Action | Source |
|----|-------|--------|--------|
| I1 | No Meta Model API access yet | Apply now | Q2 |
| I2 | The application's visual design is not yet delivered | You deliver the design drafts (your open item) | Intent review, R-03 |

## Dependencies

| ID | Dependency | Needed by | Source |
|----|-----------|----------|--------|
| D1 | Meta Model API key | Agent, benchmark, demo | Q2 |
| D2 | Your visual design drafts | The doctor chat and canvas | Intent review, R-03 |
| D3 | Selected IBD guidelines and literature | Knowledge graph content | Q5 |
| D4 | Content reviewer's time | Clinical check of the IBD pathway | intent-statement.md |
| D5 | A hosting target for the public URL (not yet chosen) | Deployment | Q7 |
| D6 | Open-weights model credits (only if used) | Optional, e.g. for the benchmark baseline | Q3 |
