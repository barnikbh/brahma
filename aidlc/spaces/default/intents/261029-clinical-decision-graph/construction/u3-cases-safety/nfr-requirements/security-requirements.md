# Security Requirements — u3-cases-safety

Upstream: `functional-spec.md` and `rules.md` (U3), `requirements.md` (NFR5–NFR8), `contract-summary.md` (C5).

- **NFR6.1 Synthetic only:** every Patient is created through `create_case` with a generated ID and the label "synthetic". There is no import path. Names are generated or demo-seeded (NFR6).
- **NFR7.1 Audit:** `update_patient` and `apply_edit` write to C2 in the same flow. A failed audit write fails the call, and no change is kept without its audit row (NFR7, FR6.5).
- **NFR8.1 Errors surfaced:** database and C1 errors raise typed `CaseError`s with a log label. Patient values are never logged (NFR8).
- **NFR8.2 Safety honesty:** a check is never `ok` without a node (BR4.3). A test asserts this for a drug with no safety nodes.
- **NFR5.1 Secrets:** U3 holds no secrets and makes no model calls (NFR5).
- **Input validation:** `update_patient` uses a field whitelist and a 0–400 kg weight range. Findings are validated (BR2). All SQL uses parameters.

## Threats Considered

- Real PHI entering through free text: mitigated by the demo disclaimer (U2) and by having no import path.
- A false "no conflict": mitigated by BR4.3.
- Silent edits: mitigated by the audit on edit.
