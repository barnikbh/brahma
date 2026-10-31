# Logical Components — u5-knowledge-updates

Upstream: `functional-spec.md`, `security-requirements.md` and `tech-stack-decisions.md` (U5), `contract-summary.md` (C1, C7, C9).

| Module | Responsibility |
|---|---|
| `brahma/updates/models.py` | Proposal, ProposalChange, LinkedSource, SourceCheckRun, DraftedChanges, VersionHistoryEntry |
| `brahma/updates/errors.py` | UpdateError and its subclasses |
| `brahma/updates/db.py` | `up_connect`: `pf_connect` plus the `up_` schema |
| `brahma/updates/repository.py` | Parameterised SQL |
| `brahma/updates/fetch.py` | SafeFetcher and the HTML-to-text step |
| `brahma/updates/copycheck.py` | 26-gram copy detection and passage selection |
| `brahma/updates/drafter.py` | The C4 structured call for `draft_proposal` |
| `brahma/updates/service.py` | UpdateService: create, draft, get, publish, reject, history, check_sources |
| `brahma/updates/check.py` | `python -m brahma.updates.check` for one scheduler run |
| `brahma/updates/api.py` | A FastAPI `router` and `feature = {name: "knowledge", version: "1.0", screens: ["knowledge"]}` (C7, C9) |

Imports go one way only: `api` → `service` → (`repository`, `fetch`, `copycheck`, `drafter`, C1, C2, C3, C4).

The api module builds the service through a dependency function, `get_update_service`, which U4's server overrides with its shared instances.
