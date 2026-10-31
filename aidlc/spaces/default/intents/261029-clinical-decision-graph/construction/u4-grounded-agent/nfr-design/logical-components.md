# Logical Components — u4-grounded-agent

Upstream:
- U4 requirements: `performance-requirements.md`, `security-requirements.md`, `scalability-requirements.md`, `reliability-requirements.md`, `observability-requirements.md` and `tech-stack-decisions.md`
- `functional-spec.md` (U4)
- `contract-summary.md` (C6, C7, C8)

| Module | What it does |
|---|---|
| `brahma/agent/models.py` | The C6 models (Claim, CheckResult, WalkResult), Walk, ExploreLane, the WalkEvent types and the form schemas |
| `brahma/agent/errors.py` | The AgentError subclasses |
| `brahma/agent/db.py` and `repository.py` | `ag_walk` and `ag_explore_lane` |
| `brahma/agent/scanner.py` | ClaimScanner |
| `brahma/agent/guard.py` | Guard: `check_line` and `check_line_by_source` (C6) |
| `brahma/agent/traverse.py` | The deterministic graph walk over C1, producing the section plan, the needed tests and out-of-knowledge |
| `brahma/agent/writer.py` | The C4 calls `extract`, `write_section` and `why` |
| `brahma/agent/engine.py` | WalkEngine: the async event stream (start, continue, rewalk, explore, stop_explore) and `run_walk` (C6) |
| `brahma/agent/logging.py` | WalkLogger |
| `brahma/server/app.py` | `create_app()`: services, middleware, core routes (C8), mounting of feature modules (C7), `/api/health` |
| `brahma/server/routes/*.py` | auth, patients and cases, walk (SSE), nodes, sessions |
| `brahma/server/__main__.py` | `python -m brahma.server`, which starts uvicorn |

Dependencies flow one way: `server` → `agent.engine` → (`traverse`, `writer`, `guard`) → C1–C5.
