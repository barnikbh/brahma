# Logical Components — u2-platform

Upstream: `security-design.md`, `security-requirements.md`, `tech-stack-decisions.md` (U2), `functional-spec.md` (U2), `contract-summary.md` (C2–C4), `unit-of-work-dependency.md` (U2 depends on nothing).

| Logical component | Responsibility | NFRs |
|---|---|---|
| `pf_connect(path)` | U2's own connection: autocommit plus explicit transactions, WAL, busy timeout, foreign keys; creates `pf_` tables and triggers, and recreates missing triggers on open | NFR7.1 |
| `ProfileRepository` | Reads and seeds `pf_profile`; shared inside U2 by Audit and Identity, so neither imports the other | NFR7.2, NFR7.3 |
| `AuditService` | C2: append, record_session, list_sessions, get_session, export_session | NFR7.1, NFR7.2, NFR6.2 |
| `PdfExporter` | fpdf2 with the bundled DejaVu Sans; header strings | NFR6.2 |
| `IdentityService` | C3: list and get profiles, disclaimer, require_role | NFR7.3 |
| `ProviderConfig` | Reads the environment; SecretStr key; HTTPS check | NFR5.1, NFR8.3 |
| `TokenBucket` | Requests-per-minute throttle | FR14.4 |
| Provider adapters | `MetaAdapter` and `LlamaHostedAdapter` (OpenAI-compatible, httpx), `ClaudeAdapter` (anthropic SDK), `RecordedAdapter` (fixture files) | NFR8.1, NFR10.1 |
| `ModelGateway` | C4: complete with timeout, retries, schema validation, call logging | NFR8.1, NFR8.2, NFR6.1, NFR11.1 |

## Derived Requirements From tech-stack-decisions.md

| ID | Design | Check |
|---|---|---|
| NFR1.1 Under 20 ms gateway overhead | The adapter call dominates; the gateway does a dict build, a token take and Pydantic validation only | Timing test with the recorded adapter: median under 20 ms |
| NFR1.2 Audit timings | Indexed `pf_session_record(created_at)` and `(case_id)` | Timing test: append and record under 50 ms; list of 1,000 under 200 ms |
| NFR9.1 80% coverage | `pytest tests/platform --cov=brahma.platform --cov-fail-under=80` | CI step |
| NFR10.1 Runs with no keys | `BRAHMA_MODEL_PROVIDER=recorded` needs no key | Start-up test with an empty environment |
| NFR11.1 One log line per call | `ModelGateway` logs one JSON line in a `finally` block | Log capture test |
| NFR12.1 Lint and types | Ruff and `mypy --strict src/brahma/platform` | CI step |

## Shared Resources and Failure Domains

| Resource or failure | Handling |
|---|---|
| Shared SQLite file | Own `pf_` tables and own connection; WAL and busy timeout |
| Provider outage | Typed error after bounded retries; the caller (U4) shows Retry |
| Rate limit | Token bucket plus Retry-After |
| PDF failure | `ExportFailed`, no partial file |
