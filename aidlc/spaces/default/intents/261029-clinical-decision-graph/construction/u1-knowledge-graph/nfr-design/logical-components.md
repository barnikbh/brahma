# Logical Components — u1-knowledge-graph

Upstream: `security-design.md`, `security-requirements.md`, `tech-stack-decisions.md`, `functional-spec.md` (U1), `contract-summary.md` (C1), `unit-of-work-dependency.md`.

U1 is a library inside the single local backend process. It has no service boundary of its own and depends on no other unit.

| Logical component | Responsibility | NFRs it carries |
|---|---|---|
| `kg_connect(path)` | U1's own connection function. Opens the SQLite file, sets `journal_mode=WAL`, `busy_timeout=5000` and `foreign_keys=ON`, and creates U1's tables, triggers and indexes if missing. Other units open the same file with their own equivalent functions; no helper is shared. | NFR8.2, NFR5.1 |
| `PackLoader` | Reads, size-checks and parses YAML with `NoAliasSafeLoader` | NFR8.1 |
| `PackValidator` | All load and version checks: BR1.1, BR1.2, BR1.4, BR3.5, plus the patient-data scan | NFR2.1, NFR6.1 |
| `KnowledgeRepository` | Tables `kg_pack`, `kg_pack_version`, `kg_node`, `kg_edge`, `kg_source`, `kg_comment`; `BEGIN IMMEDIATE` writes; immutability triggers; one-live partial unique index | NFR7.1, NFR8.2 |
| `GraphIndex` | Per-version in-memory adjacency lists and a name and synonym index, built once per version and cached; read-only | NFR1.1 |
| `ClaimMatcher` | Pure functions: normalisation, Decimal `UNIT_TABLE`, `match_claims`, `find_supporting_node` | NFR2.2 |
| `KnowledgeService` | The C1 public interface wiring the above, plus structured logging | NFR11.1 |
| `content/` | `ibd.yaml` and `urology.yaml` packs; `scripts/check_copy.py` for the authoring check | NFR12.1 (paraphrase) |

## Derived Requirements From tech-stack-decisions.md

| ID | Design | Test or check |
|---|---|---|
| NFR1.1 Search and neighbours under 50 ms up to 2,000 nodes | `GraphIndex` keeps dict-based adjacency and name lookups per version, so no SQL runs on the read path | Timing test on a generated 2,000-node fixture asserts each call under 50 ms (median of 20 runs) |
| NFR9.1 80% coverage, no network | pytest with pytest-cov `--cov=brahma.knowledge --cov-fail-under=80`; tests use a temporary SQLite file; no network calls exist in U1 | CI step fails below 80% |
| NFR10.1 Packs load under 2 s at app start | Single-pass validation; one bulk insert per table in one transaction | Timing test loading `ibd.yaml` and `urology.yaml` together asserts under 2 s |
| NFR11.1 One log line per load or version | `KnowledgeService` logs one structured JSON line per `load_pack` and `create_version`: `{event, pack, version, nodes, durationMs, result, error?}` | Test captures the log and asserts the fields |
| NFR12.1 (Ruff meaning, from tech-stack-decisions.md) | Ruff lint and format check in CI | CI step |
| NFR12.2 Full typing | All public functions and models typed; mypy `--strict` on `brahma.knowledge` in CI | CI step |

## Shared Resources

- **SQLite file** (`BRAHMA_DB_PATH`): shared with U2, U3, U5, U6 and U7, each owning its own tables and opening its own connection. U1's pragmas are set by `kg_connect`. U1 tables are prefixed `kg_`.
- **Process memory:** the `GraphIndex` cache, about 2,000 nodes at most per version, which is negligible.

## Failure Domains

| Failure | Blast radius | Handling |
|---|---|---|
| A bad pack file | That load only | PackLoadError; the previous version stays live |
| Database locked | The current write | `BEGIN IMMEDIATE` waits up to the busy timeout, then `PackBusy` is raised to the caller (NFR8) |
| Cache out of date after publish | None: versions are immutable and the cache is keyed by version ID | — |
