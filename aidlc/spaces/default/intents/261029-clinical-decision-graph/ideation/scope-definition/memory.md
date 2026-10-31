<!-- INVARIANT: examples are single-line HTML comments so a fresh template parses to total=0 (MEMORY_EMPTY). Do NOT un-comment or split across lines. t100 guards this. -->
> This file is kept up to date automatically while the stage runs. Add observations at the review step, not by editing here directly.

## Interpretations
<!-- example: 2026-05-29T10:14:32Z — chose REST over GraphQL; the consuming team only needs CRUD, revisit if subscriptions land -->
- 2026-10-29T01:52:35Z — Content-first plus both UC and Crohn's plus an Oct 31 slice conflicted; the person chose to author UC fully before Crohn's so the slice runs on UC, and declined an early API test call. Kept the API risk visible in the backlog rather than reordering against their choice.
- 2026-10-29T01:52:35Z — Benchmark cases are read as covering both branches, since the demo now spans UC and Crohn's; flagged as an assumption.

## Deviations
<!-- example: 2026-05-29T10:14:32Z — skipped the optional caching layer the stage prose suggested; the dataset is small enough that it adds risk -->

## Tradeoffs
<!-- example: 2026-05-29T10:14:32Z — picked TDD over BDD this run; the team is unit-first and the domain is well-understood -->
- 2026-10-29T01:52:35Z — Used MoSCoW for the backlog (fixed deadline, fixed scope) with a simple sequence by the person's milestones instead of WSJF scoring; WSJF adds no signal for one builder over six days.

## Open questions
<!-- example: 2026-05-29T10:14:32Z — confirm the retention window with compliance before the next stage hardens the schema -->
