# Personas

Upstream: `requirements.md` (FR11.1 demo profiles), `intent-statement.md` (target customer), `wireframes.md`.

## 1. Dr. Maya — consultant gastroenterologist (primary)

- **Role:** specialist working up and treating IBD.
- **Goals:** reach the precise sub-type faster; pick the right treatment tier; have a cited, defensible rationale.
- **Pain points:** guidelines are long and scattered; senior pathway knowledge isn't written down; AI chatbots state things with no source.
- **Context:** uses Brahma live in a consult (needs to scan it in seconds) and before or after one (case prep, follow-up review). Medium tech comfort: wants clarity, not dashboards.
- **Demo profile:** "Dr. Maya (gastroenterologist)".

## 2. Demo urologist — second specialty

- **Role:** a urologist walking a simple case through the urology stub pack.
- **Goal:** see that the same tool works outside IBD.
- **Context:** exists to show the knowledge model generalises (FR3). Uses the same screens as Dr. Maya.
- **Demo profile:** "Demo urologist".

## 3. Clinical reviewer

- **Role:** a clinician who checks proposed knowledge changes before they go live.
- **Goals:** publish only changes that are sourced and paraphrased; see exactly what changes and why.
- **Pain points:** AI-drafted content that may copy or misread a source.
- **Context:** works only on the Knowledge screen. In the demo this is a seeded profile; in real life it would be the family or friend clinician who reviews the IBD content.
- **Demo profile:** "Demo clinical reviewer".

## Relationships and priority

1. **Dr. Maya** is the primary persona. Every Must story is hers.
2. The **clinical reviewer** receives the changes Dr. Maya suggests (US8.1 → US8.2).
3. The **demo urologist** reuses Dr. Maya's flows on another pack (US9.1).

There is no judge persona (Q3).
