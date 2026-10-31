# Discovered Rules — Clinical Decision Graph

> Hard constraints only, each stated by the builder in the interview or carried from the hackathon, the builder-approved constraint register, or the builder's workspace rules. All are confirmed in the Practices Discovery consolidated summary.

## Mandated

- ALWAYS run the submitted demo and the benchmark on a Meta model through the Meta Model API. Claude is used only for building and for drafting knowledge content. (Q9; constraint-register.md C-T1)
- ALWAYS show "Decision support, not diagnosis" on every screen and every answer. (constraint-register.md C-R2; consolidated summary)
- ALWAYS ground every line of an answer in a cited knowledge-graph node and its source. Never answer from model memory. (constraint-register.md C-T3; consolidated summary)
- ALWAYS keep secrets (model API keys, session secrets, demo-account passwords) in environment variables. Only placeholder names go in `.env.example`. (workspace owner rule; consolidated summary)
- ALWAYS paraphrase and cite guideline content in knowledge-graph nodes. (constraint-register.md C-R4)
- ALWAYS submit (public repository plus demo video) before Nov 4, 2026, 9:00 PM ET. (constraint-register.md C-O1; Q8)

## Forbidden

- NEVER use, load or store real patient data, or connect to an EHR. Only synthetic or de-identified cases are allowed. (constraint-register.md C-R1)
- NEVER commit secrets, API keys or credentials to the public repository, whether in code, config or commit history. (workspace owner rule; consolidated summary)
- NEVER commit plaintext `data/*.json` files. (workspace owner rule)
- NEVER present the tool's output as a diagnosis, and never claim HIPAA compliance or any certification. (constraint-register.md C-R2, C-R3)
- NEVER copy copyrighted guideline text verbatim into the knowledge graph. (constraint-register.md C-R4)
