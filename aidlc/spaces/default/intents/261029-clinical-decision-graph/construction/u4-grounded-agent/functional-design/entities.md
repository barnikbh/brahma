# Entities — u4-grounded-agent

Upstream: `unit-of-work.md` (U4), `contract-summary.md` (C6, C8 and the R-02 additions), `components.md` (GroundedAgent, BackendServer).

The code lives in the module `brahma.agent` (the walk and the guard) and `brahma.server` (HTTP). Tables use the `ag_` prefix in the shared SQLite file.

| Entity | Key fields | Notes |
|---|---|---|
| Walk | walkId, caseId, packVersion, liveVersionAtStart?, status (`paused`, `answered`, `needs_data`, `out_of_knowledge` or `error`), waitingFor?, findings (JSON), answers (JSON), pathNodeIds[], sections (JSON: emitted lines per section), lastSectionDone?, counts {steps, cited, ungrounded}, provider, model, startedAt, endedAt? | Resumable after `paused` or `error` (FR5.9). |
| ExploreLane | laneId, walkId, branchNodeId, nodeIds[], lines (JSON), status (`open`, `stopped`) | Kept apart from the main sections (FR4.7). |
| RejectedLine (value) | text, citedNodeIds, failures | Not stored here: written to the C2 audit as `line_rejected`. |
| Claim, CheckResult, WalkResult | C6 models | Value objects. |
| WalkEvent | type (progress, form, paused, map_update, line, section_done, done or error) and payload | The SSE event shapes from C8. |

## Summary

There are two stored entities (Walk and ExploreLane) and several value objects. A Case (U3) has many Walks, and a Walk has many ExploreLanes.
