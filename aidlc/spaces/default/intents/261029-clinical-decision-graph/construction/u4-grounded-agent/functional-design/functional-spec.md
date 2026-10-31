# Functional Specification — u4-grounded-agent

Upstream:
- `unit-of-work.md` (U4) and `unit-of-work-story-map.md`
- `stories.md`: US3.1–US3.6, US7.1, US9.1
- `requirements.md`: FR4, FR5, FR9.3, FR12, FR14.3, FR15
- `components.md`: GroundedAgent, BackendServer
- `contract-summary.md`: C1–C8 and the R-02 additions

Data is described in `entities.md`, and rules in `rules.md`.

## Purpose

`brahma.agent` provides:
- the grounding guard: `check_line` and `check_line_by_source` (C6)
- the walk engine: `WalkEngine.run_walk`, which also streams events

`brahma.server` is the local FastAPI app (C8). It wires C1–C5 together and mounts U5, U6 and U7 (C7).

## Workflows

- **W1 Start:** extract findings → set_findings → confirm-findings form → paused (BR2.1).
- **W2 Continue:** traverse (BR2.2) → needs-data form → paused (BR2.3). Otherwise, for each section in order: write (BR2.5) → check (BR1) → line events → section_done → why (BR2.6) → done, then record the session (BR4.5).
- **W3 Out of knowledge:** BR2.4.
- **W4 Explore and stop:** BR2.8.
- **W5 Re-walk:** BR2.7.
- **W6 Retry:** BR3.
- **W7 Server routes:** profiles, session, disclaimer, patients, case view, lock, messages, patient patch, form drafts, walk (SSE), map, node detail and comments, treatment edits, and sessions with export (C8). Each route delegates to C2, C3 or C5.
- **W8 `run_walk`:** U7 runs a walk without SSE, auto-answering forms with the supplied answers.

## State Machines

A Walk moves as follows:
- `paused` → (`paused` | `answered` | `needs_data` | `out_of_knowledge` | `error`)
- `error` → `paused` | `answered` (on retry)

An ExploreLane moves from `open` to `stopped`.

## Entity Relationships (derived from entities.md)

A Case (U3) has many Walks, and a Walk has many ExploreLanes. Each finished Walk produces one SessionRecord in U2.

## Rules Summary (derived from rules.md)

The rules fall into four groups: the guard (BR1), the walk (BR2), failure and resume (BR3), and the server (BR4).

## Error Handling

- `AgentError` subclasses: WalkNotFound, WalkNotResumable, FindingsNotReady.
- Over HTTP, every error uses the C8 `Error` shape. During a walk, errors arrive as `error` events.
- Gateway errors keep their `retryable` flag. The log records the provider name, never any keys (AC3.4.2).

## Acceptance Criteria Handled Elsewhere

These are delivered by u8-web-app:
- the layout, selection sync, symbols, keyboard use and light-up animation (AC3.5.1–AC3.5.4)
- the map data these screens need, which U4 provides through `/map` and `map_update` events
