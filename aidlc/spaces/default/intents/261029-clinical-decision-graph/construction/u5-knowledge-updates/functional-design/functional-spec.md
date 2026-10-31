# Functional Specification — u5-knowledge-updates

Upstream: `unit-of-work.md` (U5), `unit-of-work-story-map.md`, `stories.md` (US8.1–US8.3), `requirements.md` (FR10), `components.md` (KnowledgeUpdates), `contract-summary.md` (C1, C2, C3, C4, C7, C9, X2). Data is described in `entities.md` and rules in `rules.md`.

## Purpose

`brahma.updates` holds `UpdateService` plus a C9 HTTP router (`brahma.updates.api`), which mounts at `/api/knowledge` under the C7 convention. It uses C1 for nodes and versions, C2 for the audit, C3 for roles and C4 for drafting.

## Workflows

- **W1 Suggest:** `create_proposal(nodeId, change, comment, sourceUrl?, section?, proposer)` follows BR1.1 and BR1.2. When a URL is given, the source is fetched and linked (BR2), and the copy check runs (BR2.3).
- **W2 Draft from a source:** `draft_from_source(pack, url, proposer)` fetches the source (BR2), drafts the changes (BR3) and stores a proposal.
- **W3 Review:** `get_proposal` returns the before and after values, the passages and the flags. `publish` follows BR1.3–BR1.5 and `reject` follows BR1.6.
- **W4 History:** `version_history(pack)` follows BR1.7.
- **W5 Scheduled check:** `check_sources()` follows BR4.

## State Machines

A Proposal moves from `proposed` to either `published` or `rejected`. Both end states are terminal.

## Entity Relationships (derived from entities.md)

A Proposal has one or more ProposalChanges. A LinkedSource can be referenced by many proposals. A SourceCheckRun records many source checks.

## Rules Summary (derived from rules.md)

The rules fall into four groups: proposals (BR1), sources (BR2), drafting (BR3) and the scheduler (BR4).

## Error Handling

- Errors are typed `UpdateError` subclasses with a `log_label`: ProposalNotFound, ProposalClosed, CopyFlagged, SourceFetchError and DraftFailed. C1 validation errors and C3 Forbidden pass through unchanged.
- The API maps them to status codes: 404, 409 for CopyFlagged and ProposalClosed, 403, 422 for a URL or validation error, and 502 for fetch or draft failures. Each response carries a plain message, so the form can keep the doctor's input (FR10.8).

## Acceptance Criteria Handled Elsewhere

u8-web-app delivers the screens: the before-and-after layout and the input kept in the form.
