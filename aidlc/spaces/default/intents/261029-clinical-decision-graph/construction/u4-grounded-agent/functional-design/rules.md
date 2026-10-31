# Business Rules — u4-grounded-agent

Upstream: `requirements.md` (FR4, FR5.8, FR5.9, FR9.3, FR12, FR14.3, FR15), `stories.md` (US3.1–US3.6, US7.1, US9.1), `contract-summary.md` (C1–C6, C8).

## Grounding guard (BR1, FR4.10)

- **BR1.1** `check_line(text, citedNodeIds, version, caseId)` builds the claims from two sources:
  - the claims the model returns, which are structured C6 claims;
  - a deterministic scan of the text, which finds every number with a unit (dose, threshold) and every drug, test or diagnosis name or synonym known to the pinned version.

  Claims found by the scan are added even if the model did not list them, so a dose can't be hidden by leaving it out of the claims.
- **BR1.2** Each claim must match a field of a cited node exactly after unit normalisation (C1 `match_claims`). For a per-kg drug, a dose claim may also match the case's computed dose (C5 `compute_dose`).
- **BR1.3** A line passes only when every claim matches and it cites at least one node from the pinned version. A line with no claims passes only if it cites a node. Section headers are fixed text and are not checked.
- **BR1.4** A failed line is never sent. The ungrounded count goes up by one, and `line_rejected` (text, cited IDs, failures) is written to the audit.
- **BR1.5** `check_line_by_source` follows C6 R-03 and uses C1 `find_supporting_node` per cited source.

## Walk (BR2, FR4)

- **BR2.1 Extract.** `start` sends the doctor's text to C4 (purpose `extract`, structured output). It produces finding chips, which C5 `set_findings` validates. The walk then posts a `confirm-findings` form and pauses (AC3.1.1).
- **BR2.2 Traverse.** On `continue` with confirmed findings (when C5 `findings_ready` is true), the traversal is deterministic and works only on the graph:
  1. C1 `search(version, facts)` gives the candidate diagnosis.
  2. C1 `neighbours` follows edges whose conditions match the findings and answers, in the order tests → sub-type → treatment tiers (entry tier marked) → monitor → diet → watch-outs and escalation.

  The model never picks nodes.
- **BR2.3 Needs data.** When a required test node has no result, the walk posts a `needs-data` form naming those tests and pauses. Unanswered tests stay "not yet tested", and the walk goes as far as the answered ones allow (FR4.4, AC3.3.2).
- **BR2.4 Out of knowledge.** When no pack matches the findings, the outcome is `out_of_knowledge`. The answer is the fixed text "No grounded answer" with the "Suggest adding this branch" action. No model call is made and no diagnosis or treatment line is sent (FR4.5).
- **BR2.5 Write.** For each section in the FR4.6 order, C4 (purpose `write_section`) gets only the walked nodes for that section and their sources. It returns lines, each with its node IDs and claims. Every line goes through BR1, and only lines that pass are sent.
- **BR2.6 Why.** The "why" works the same way (purpose `why`), one line per sentence (FR9.3, AC7.1.2).
- **BR2.7 Pin.** The walk uses the case's pinned version, and the first walk pins it (C5 `pin`). A `rewalk` with a newer live version re-pins the case and records both versions (FR1.7).
- **BR2.8 Explore.** `explore` traverses from the alternative node into a lane (same guard), and the main sections stay unchanged. `stop_explore` closes the lane and writes `explored_not_acted` to the audit (FR4.7, AC3.6.2).
- **BR2.9 Free text during a walk.** A chat message sent while a walk is running is stored. When the walk ends, Brahma offers "Review findings and re-walk" (FR4.8).
- **BR2.10 Pack selection.** The pack is chosen by search across every live pack, so urology needs no code of its own (AC9.1.2).

## Failure and resume (BR3, FR5.9)

- **BR3.1** If a gateway error or a guard exception happens mid-stream, the stream sends an `error` event (code, plain message, retryable) and the walk is saved as `error`, with every input and every section completed so far.
- **BR3.2** `continue` with the same walkId resumes after `lastSectionDone`. Lines already sent are never sent again.

## Server (BR4, C8)

- **BR4.1** The server is FastAPI. It mounts the core routes (C8), plus each module listed in `BRAHMA_FEATURE_MODULES` under `/api/<feature name>`, and serves `/api/features` (C7).
- **BR4.2** Sessions use a signed cookie holding the profileId, with the secret taken from `BRAHMA_SESSION_SECRET`. Any route except profiles and sign-in returns 401 when no one is signed in. The server sets `X-Brahma-Profile` for mounted routers from this session; a value sent by the client is ignored.
- **BR4.3** Walk and edit routes need the tab lock and return 409 `case_read_only` without it.
- **BR4.4** The first `progress` event is sent before any model call, within 3 s (NFR1).
- **BR4.5** Each finished walk records a SessionRecord (C2) with the profile, pack version, provider, model, inputs, node path, answer lines and sources (AC7.1.1).
- **BR4.6** Every `done` event and every NodeDetail carry the pack version. The web app shows the disclaimer (FR15.1).
- **BR4.7** Logging: each walk writes its node path, model call metadata and any errors to the log file `BRAHMA_LOG_PATH` (NFR11).

## Summary

There are 23 rules in four groups. The model only writes text from nodes the deterministic walk has already chosen, and every line passes the guard before it is sent.
