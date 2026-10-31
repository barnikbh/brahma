# Entities — u3-cases-safety

Upstream: `unit-of-work.md` (U3), `contract-summary.md` (C5), `components.md` (Cases, TreatmentSafety).

Module `brahma.cases`. The tables use the prefix `cs_` in the shared SQLite file, through U2's `pf_connect`-style connection (WAL).

| Entity | Key fields | Notes |
|---|---|---|
| Patient | patientId, syntheticName, age, sex, weightKg?, pregnancyStatus?, comorbidities[], allergies[], currentMedication[] | Synthetic only. Exactly one Patient per Case. |
| Case | caseId (`BR-` + 6 chars, labelled synthetic), patientId, ownerProfileId, pinnedPackVersion?, origin `clinic\|benchmark`, benchmarkRunId?, status | status is one of `new`, `needs_data`, `answered`, `out_of_knowledge`, `follow_up_due`. |
| Message | messageId, caseId, author, kind, body (JSON), formKind?, formState?, createdAt | Append-only thread. A form moves from `open` to `submitted` only. |
| FormDraft | caseId, messageId, values (JSON) | Unsubmitted values. Deleted when the form is submitted. |
| Finding | findingId, caseId, kind, name, value?, unit?, enteredValue?, duration?, validationState | Replaced as a set by `set_findings`. |
| TabLock | caseId, tabId, heartbeatAt | One row per case. Expires 45 s after the last heartbeat. |
| TreatmentEdit | editId, caseId, nodeId, original (JSON), newValues (JSON), editorProfileId, createdAt | Append-only. The latest edit per (case, node) is the one in effect. |
| SafetyResult, DoseResult, MissingWeight | value objects | Not stored. |

## Summary

There are seven stored entities and three value objects. Case owns Patient, Message, FormDraft, Finding, TabLock and TreatmentEdit, all keyed by caseId.
