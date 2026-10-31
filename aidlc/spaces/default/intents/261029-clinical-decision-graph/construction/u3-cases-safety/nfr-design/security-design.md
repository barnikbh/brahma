# Security Design — u3-cases-safety

Upstream: `security-requirements.md` and `tech-stack-decisions.md` (U3), `functional-spec.md` (U3), `contract-summary.md` (C5).

- **Synthetic IDs (NFR6.1):** `new_case_id()` returns `BR-` followed by 6 characters from `secrets.token_hex`. Every Case carries `synthetic=True`. There is no import function.
- **Audit with the change (NFR7.1):** `update_patient` and `apply_edit` run the `cs_` write and the C2 `append` inside one `transaction()` on the shared connection. If either step fails, both roll back.
- **Typed errors (NFR8.1):** a `CaseError` base class with `log_label`. Logs hold the caseId, the operation and the error class, never patient values.
- **Safety honesty (NFR8.2):** `SafetyResult` has a model validator that rejects `status="ok"` with an empty `node_ids`. So an "ok" without a node can't be constructed.
- **Validation:** `PatientChange` is a Pydantic model with `extra="forbid"` and weight between 0 and 400. All SQL uses parameters.
- **NFR5.1:** U3 holds no secrets, so there is nothing to design.
