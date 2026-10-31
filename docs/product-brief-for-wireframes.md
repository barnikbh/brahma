# Product Brief: Clinical Decision Graph (for wireframing)

A decision-support workspace for specialist doctors. It turns the pathway an experienced doctor carries in their head, from symptoms to diagnosis to treatment, into an explicit, walkable and auditable map. Every answer comes from a curated clinical knowledge graph, never from the AI's own memory, and every step shows its source.

> Decision support, not diagnosis. Synthetic patients only. Built for the Meta Global AI Developer Hackathon (Theme 2, Indie track). Submission due Nov 4, 2026.

---

## 1. The problem

When a doctor sees a patient, they hear things like *frequent bloody stool for 6 months* (symptoms) and see results like *low hemoglobin and high stool calprotectin* (metrics). From that they form a working diagnosis, for example inflammatory bowel disease (IBD).

To confirm it and narrow it to the most specific diagnosis (for example *ulcerative colitis, pancolitis, severe*), they order more diagnostics. Then they plan treatment, which is tiered: try mesalamine first, then steroids, then biologics, and within biologics choose between options such as Stelara or Remicade. Alongside that they track metrics to judge improvement, manage diet, watch for warning signs, and know what would lead to surgery.

**All of this lives in the doctor's head, built from experience.** General AI chatbots can't be trusted here because they state things with no source. This product makes that layer visible, walkable and auditable by the doctor.

IBD is the first example. The model is built for every specialty (oncology, urology and beyond), and treatment plans can extend to medicine, diet, physiotherapy and more.

## 2. Who it's for

**Primary persona: Dr. Maya, consultant gastroenterologist**
- **Goals:** reach the precise sub-type faster; pick the right treatment tier; have a defensible, cited rationale.
- **Pain points:** guidelines are long and scattered; senior pathway knowledge isn't written down; AI tools hallucinate and can't be audited.
- **When she uses it:** live during a consultation (fast, scannable) and before or after one (case prep, follow-up review, deeper reading).
- **Tech comfort:** medium. She wants clarity, not dashboards.

## 3. Core user story (the demo)

> **As a specialist, I want to describe a patient's symptoms and metrics and have the system walk the clinical decision graph with me, so that I can see the working diagnosis, the tests that confirm and refine it, and the tiered treatment plan, with every step cited and auditable.**

### The walk, step by step

1. **Sign in.** Dr. Maya signs in with a demo account. Every session is tied to her identity for the audit trail.
2. **Describe the patient.** She enters the picture, for example: *"34-year-old, bloody stool on and off for 6 months, Hb 10.2 g/dL, faecal calprotectin 850 µg/g."*
3. **Confirm what was understood.** The system reflects back the symptoms (with duration) and metrics (with values and units) it picked up, so she can correct them before it walks.
4. **Working diagnosis.** The agent walks the graph: these findings point to IBD. It shows why, which nodes it matched, and their sources.
5. **Confirm and refine.** It lists the additional diagnostics that confirm the diagnosis and narrow it (for example colonoscopy with biopsy, extent mapping, severity scoring). It shows how each result branches: ulcerative colitis or Crohn's disease, then extent and severity.
6. **Precise sub-type.** With the extra results entered, it lands on the specific diagnosis, for example *ulcerative colitis, pancolitis, severe*.
7. **Treatment plan, tiered.** It shows the ladder: first line (e.g. mesalamine), then escalation (e.g. steroids), then advanced therapy (biologics, with the options and when each fits). Each tier shows its entry criteria.
8. **Monitor, diet, watch-outs.** It shows the metrics to keep watching and their thresholds, the diet guidance, and the warning signs and escalation triggers, including what would lead to surgery.
9. **Every line is cited.** Any step can be clicked to see the node on the canvas, its source, its knowledge version and its comments.
10. **Session is audited.** The whole walk is saved: inputs, the path through the graph, sources, the answer, and a plain-language explanation of why.

### Acceptance (what "done" looks like for the demo)
- A synthetic IBD patient goes from symptoms and metrics to a precise sub-type, a treatment tier and a monitoring plan in one session.
- **Zero ungrounded claims:** every recommendation links to a graph node and its source.
- The canvas shows exactly the part of the graph used in the session.
- The session appears in the audit history with its path and explanation.
- "Decision support, not diagnosis" is visible on every answer and screen.

## 4. Supporting user stories

| # | Story | Why it matters |
|---|-------|----------------|
| S1 | As a specialist, I want to **see the part of the knowledge graph the agent used**, highlighted on a canvas, so I can check its reasoning at a glance. | Trust and explainability |
| S2 | As a specialist, I want to **click any step or node** and see its content, source, version and comments, so I can verify it. | Auditability |
| S3 | As a specialist, I want to **review past sessions**, each with its inputs, path, sources and explanation, so I can revisit and defend a decision. | Audit layer |
| S4 | As a specialist, I want to **link a new source or suggest a change** to the knowledge, and see it become a new version with my comment, so the knowledge stays current. | Update layer |
| S5 | As a specialist, I want to **see the knowledge version and change history** with comments, so I know what changed and why. | Versioning |
| S6 | As a judge or reviewer, I want to **see benchmark results** (about 20 synthetic cases, at least 95% of recommendations grounded, against a plain AI model with no graph), so I can see the grounding works. | Proof for judges |
| S7 | As a judge or reviewer, I want to **see a second specialty** (a small urology stub) running through the same model, so I can see it generalises beyond IBD. | Proof for judges |

## 5. Screens to wireframe

| Screen | Purpose | Key elements |
|--------|---------|--------------|
| **Sign-in** | Enter as a demo doctor | Demo account picker or simple login; disclaimer |
| **Consultation workspace** (main screen) | The walk | Patient input; extracted symptom and metric chips (editable); agent answer as a pathway; canvas of the graph region used; citation chips linking answer ↔ canvas; disclaimer |
| **Node detail panel** | Verify one step | Node content, type (symptom, metric, diagnosis, test, treatment tier, monitoring, diet, watch-out, escalation), source citation, version, comments, "suggest a change" |
| **Session history / audit** | Revisit decisions | Session list (date, patient summary, outcome); session detail: inputs, path walked, sources, answer, plain-language "why" |
| **Knowledge update** | Keep knowledge current | Link a source (URL or document); describe the change; see the proposed new version; comment; version history |
| **Benchmark results** | Proof of grounding | 20 cases; grounded-answer score per case; tool vs. plain-model comparison; overall pass/fail against 95% |

### The pathway answer (main content of the workspace)
A structured, scannable sequence, each line with a citation chip:
**Findings → Working diagnosis → Confirm with (tests) → Refined sub-type → Treatment tiers (1st line → escalation → advanced) → Monitor (metrics and thresholds) → Diet → Watch-outs and surgery triggers**

### States to include
- **Empty:** first visit, no patient entered yet; a prompt with an example.
- **Working:** the agent is walking; the path lights up progressively on the canvas.
- **Answered:** the full pathway with citations.
- **Needs more data:** the agent asks for the specific test result it needs to refine further.
- **Out of knowledge:** the graph has no grounded answer; say so plainly, never guess.
- **Error:** the model or service is unavailable; plain message and a retry.

## 6. Design principles and constraints

- **Grounded or silent.** Nothing appears without a source. If the graph can't answer, the UI says so.
- **Scannable live, deep on demand.** The consultation view must be readable in seconds; detail sits behind a click (progressive disclosure).
- **The canvas mirrors the answer.** Selecting an answer line highlights its node, and selecting a node highlights the answer line.
- **Always visible:** "Decision support, not diagnosis", plus the knowledge version in use.
- **Synthetic data only.** No real patient identifiers anywhere.
- **Accessibility:** WCAG 2.1 AA basics: keyboard navigable, sufficient contrast, status never shown by color alone.
- **Form factor:** desktop and laptop first (your call on tablet).

## 7. Open design decisions for your wireframes

These are the calls your wireframes will settle. Options are listed; pick what fits your vision.

1. **Workspace layout:** split view (chat left, canvas right), canvas-centred with chat in a drawer, or chat-centred with the canvas on demand.
2. **Answer format:** structured pathway card, conversational text with citations, or a short summary above the card.
3. **Patient input:** free text, a structured intake form, or free text converted into editable chips.
4. **Which secondary screens** make the first version: audit history, knowledge update, node detail, benchmark page.
5. **Devices:** desktop only, or also tablet or phone.

---

*Source: your project description and the approved intent, feasibility and scope documents in `aidlc/spaces/default/intents/261029-clinical-decision-graph/ideation/`.*
