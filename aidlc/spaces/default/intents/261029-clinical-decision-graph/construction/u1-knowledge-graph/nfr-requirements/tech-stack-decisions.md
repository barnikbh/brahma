# Tech Stack Decisions — u1-knowledge-graph

Upstream: `requirements.md` (C-T2 Python backend; NFR9, NFR12), `team-practices.md` (Ruff, pytest, 80% coverage), `contract-summary.md` (C1 Pydantic models; open question on pack format), `functional-spec.md` and `rules.md` (U1).

| Area | Decision | Why | Requirement IDs |
|---|---|---|---|
| Language | Python 3.12 | Approved stack (C-T2) | — |
| Models | Pydantic v2 for Node, Edge, Fact, Step, ChangeSet, Claim | Shared with C1 and the HTTP API; validation built in | NFR12.2 |
| Pack file format | YAML, parsed with `yaml.safe_load` | Easiest to author and review by hand; settles the C1 open question | NFR8.1, NFR12.2 |
| Storage | SQLite (standard library `sqlite3`), one shared file, U1-owned tables | Local, no setup, transactional | NFR8.2, NFR10.1 |
| Graph traversal | Plain Python over adjacency lists loaded per version | The packs are small (hundreds of nodes); no graph database needed | NFR1.1 |
| Unit conversion | A small hand-written table per measure | Exact and testable; no conversion library needed | NFR2.2 |
| Tests | pytest with pytest-cov | Team practice | NFR9.1 |
| Lint and format | Ruff | Team practice | NFR12.1 |

## Derived Requirements

| ID | Requirement | Source |
|---|---|---|
| NFR1.1 | `search` and `neighbours` each return in under 50 ms for packs up to 2,000 nodes, so the 60-second walk budget goes to the model calls | NFR1 |
| NFR9.1 | U1 line coverage is at least 80%, measured on its own package, and runs in CI with no network | NFR9 |
| NFR10.1 | U1 needs nothing installed beyond Python and the project's dependencies; the IBD and urology packs load at app start in under 2 s | NFR10 |
| NFR11.1 | Pack loads and version creation write one log line each (pack, version, node count, duration, result) | NFR11 |
| NFR12.1 | Ruff passes with no errors in CI | NFR12 |
| NFR12.2 | All public functions and models are fully typed, matching C1 | NFR12 |
