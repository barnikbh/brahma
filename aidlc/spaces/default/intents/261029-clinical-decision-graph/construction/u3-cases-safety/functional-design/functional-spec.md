# Functional Specification — u3-cases-safety

Upstream: `unit-of-work.md` (U3), `unit-of-work-story-map.md`, `stories.md` (this unit implements part of US2.1, US3.1, US4.1 and US4.2), `requirements.md` (FR1.6, FR1.7, FR4.9, FR4.11, FR6, FR12), `components.md` (Cases, TreatmentSafety), `contract-summary.md` (C5, which uses C1 and C2). Data is in `entities.md` and rules are in `rules.md`.

## Purpose

`brahma.cases` is a library that provides `CaseService` (C5). It depends on `KnowledgeService` (C1) for nodes and units, and on `AuditService` (C2) for the audit trail.

## Workflows

- **W1 Create, search, reopen:** `create_case`, `search_patients` and `get_case`, `get_patient`, `list_messages`, `get_form_drafts` (BR1.1, BR1.2, FR12.3).
- **W2 Confirm findings:** `set_findings` validates each finding (BR2.1–BR2.6) and replaces the set. `findings_ready` gates the walk (BR2.7).
- **W3 Walk bookkeeping:** U4 calls `pin`, `append_message` and `newer_version` (BR1.3, BR1.5).
- **W4 Patient change:** `update_patient` writes to the audit. The caller then re-runs `compute_dose` and `safety_checks` (BR1.4).
- **W5 Treatment panel:** `compute_dose` and `safety_checks` (BR4.1–BR4.3).
- **W6 Edit:** `apply_edit` (BR4.4).
- **W7 Tab lock:** `acquire_lock` is used for the heartbeat, every 15 s, and `release_lock` on close (BR3).

## State Machines

- **Case status:** `new` → `needs_data` | `answered` | `out_of_knowledge`. `answered` → `follow_up_due`. A re-walk may go back to any of these. U4 sets the status through `set_status`.
- **Form message:** `open` → `submitted`.

## Entity Relationships (derived from entities.md)

A Case has one Patient. It has many Messages, FormDrafts, Findings and TreatmentEdits, and at most one TabLock.

## Rules Summary (derived from rules.md)

There are four groups: cases (BR1), findings (BR2), lock (BR3), and dose and safety (BR4).

## Error Handling

Errors use typed `CaseError` subclasses carrying the U2-style `log_label`:
- `CaseNotFound`
- `InvalidPatientChange`
- `NodeNotFound`, which comes from C1
- `NotADrugNode`
- `FormAlreadySubmitted`

Database errors are raised; they are never ignored. MissingWeight is a result, not an error.

## Acceptance Criteria Handled Elsewhere

These are delivered by u8-web-app:
- Banners and chips: AC2.1.3 display.
- Chat parsing of "she's 62 kg" and the edit form UI: AC3.1.3, AC4.2.1.

The chip extraction in AC3.1.1 is delivered by u4-grounded-agent.
