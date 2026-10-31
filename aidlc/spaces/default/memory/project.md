# Project-Level Rules

> Project-specific specialisation and corrections. Loaded after `org.md` and
> `team.md` as strict-additive guidance; contradictions with broader policy
> are rejected. Populated by practices-discovery and the self-learning loop.
>
> Use sparingly: most teams don't need a project layer. Reach for it
> only when this specific project needs stable, durable guidance beyond the
> team practice (for example, package-specific release checks or an additional
> regression suite for a legacy component).

## Way of Working

<!-- Project-specific specialisation. Example: -->
<!-- This monorepo requires package-scoped branch names and a package owner -->
<!-- review in addition to the team's normal merge policy. -->

## Walking Skeleton

<!-- Project-specific specialisation. Example: -->
<!-- The walking skeleton must exercise the legacy service adapter as well -->
<!-- as the new service boundary. -->

## Testing Posture

<!-- Project-specific specialisation. -->

## Guard Policy

<!-- Project-specific. Mode: strict, relaxed, or off. Strict here holds for every intent, whatever one person asks in chat; relaxed or off here applies to every intent whose policy came from its scope, unless the person sets another; changing this line changes it. A section under the retired Change Control heading, written by an earlier release, is still read. -->

## Deployment

<!-- Project-specific specialisation. -->

## Code Style

<!-- Project-specific specialisation. -->

## Tech Stack

<!-- Technology choices locked for this project. -->

## Decided

<!-- Decisions made in earlier stages that should not be re-asked. -->
<!-- Format: DECIDED: [decision] (Stage [slug], [date]) -->

## Scope Overrides

<!-- Custom scope rules for this project. -->

## Forbidden

<!-- Populated by practices-discovery affirmation gate. -->
<!-- Format: NEVER [behavior] (affirmed [date]) -->
<!-- Example: NEVER throw exceptions across service layer boundaries (affirmed 2026-05-17) -->

- NEVER use, load or store real patient data, or connect to an EHR. Only synthetic or de-identified cases are allowed. (constraint-register.md C-R1) (affirmed 2026-10-29)

- NEVER commit secrets, API keys or credentials to the public repository, whether in code, config or commit history. (workspace owner rule; consolidated summary) (affirmed 2026-10-29)

- NEVER commit plaintext `data/*.json` files. (workspace owner rule) (affirmed 2026-10-29)

- NEVER present the tool's output as a diagnosis, and never claim HIPAA compliance or any certification. (constraint-register.md C-R2, C-R3) (affirmed 2026-10-29)

- NEVER copy copyrighted guideline text verbatim into the knowledge graph. (constraint-register.md C-R4) (affirmed 2026-10-29)

## Mandated

<!-- Populated by practices-discovery affirmation gate. -->
<!-- Format: ALWAYS [behavior] (affirmed [date]) -->
<!-- Example: ALWAYS use Result<T,E> for fallible operations in service layer (affirmed 2026-05-17) -->

- ALWAYS run the submitted demo and the benchmark on a Meta model through the Meta Model API. Claude is used only for building and for drafting knowledge content. (Q9; constraint-register.md C-T1) (affirmed 2026-10-29)

- ALWAYS show "Decision support, not diagnosis" on every screen and every answer. (constraint-register.md C-R2; consolidated summary) (affirmed 2026-10-29)

- ALWAYS ground every line of an answer in a cited knowledge-graph node and its source. Never answer from model memory. (constraint-register.md C-T3; consolidated summary) (affirmed 2026-10-29)

- ALWAYS keep secrets (model API keys, session secrets, demo-account passwords) in environment variables. Only placeholder names go in `.env.example`. (workspace owner rule; consolidated summary) (affirmed 2026-10-29)

- ALWAYS paraphrase and cite guideline content in knowledge-graph nodes. (constraint-register.md C-R4) (affirmed 2026-10-29)

- ALWAYS submit (public repository plus demo video) before Nov 4, 2026, 9:00 PM ET. (constraint-register.md C-O1; Q8) (affirmed 2026-10-29)

## Corrections

<!-- Project-specific corrections from human feedback. -->
<!-- Format: NEVER/ALWAYS [behavior] (learned [date]) -->
- Keep process detail light for this hackathon: skip fine-grained process choices (such as story sizing) and pick a sensible lightweight default instead of asking. (learned 2026-10-29) <!-- cid:261029-clinical-decision-graph:user-stories:fa882d95212f237785726ba3e1e5c2f5d3cc125f7b827a184c8cbd4ae8b659bf -->
