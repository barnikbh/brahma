# Logical Components — u3-cases-safety

Upstream: `functional-spec.md`, `security-requirements.md` and `tech-stack-decisions.md` (U3), `contract-summary.md` (C5).

| Module | Responsibility |
|---|---|
| `brahma/cases/models.py` | C5 Pydantic models: Patient, Case, Message, Finding, SafetyResult, DoseResult, MissingWeight, TreatmentEdit, PatientChange |
| `brahma/cases/errors.py` | CaseError and its subclasses |
| `brahma/cases/db.py` | `cs_connect`: the `cs_` schema on the shared SQLite file in WAL mode |
| `brahma/cases/repository.py` | Parameterised SQL for every entity |
| `brahma/cases/findings.py` | FR4.11 validation (BR2), using C1 nodes and U1 units |
| `brahma/cases/safety.py` | `compute_dose` and `safety_checks` (BR4.1–BR4.3), as pure functions over nodes and the patient |
| `brahma/cases/service.py` | `CaseService`, the C5 facade that wires the repository, C1, C2 and the lock |

Dependencies point one way only: `service` → (`repository`, `findings`, `safety`, C1, C2). The `safety` module is pure, so U4's grounding guard can call it directly. To read the drug and safety nodes, `safety` gets the pinned version's nodes by type through the C1 `search`/`get_node` index.
