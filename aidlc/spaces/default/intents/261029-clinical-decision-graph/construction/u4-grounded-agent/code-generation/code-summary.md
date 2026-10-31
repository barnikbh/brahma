# Code Summary — u4-grounded-agent

## Built

**`brahma.agent`:**
- **ClaimScanner and Guard:** a line passes only if its declared and scanned claims match a node the walk chose. Per-kg doses can match either the node's value or the computed dose.
- **Deterministic traversal:** IBD and urology are both reached through a search across all live packs.
- **Writer:** C4 calls for extract, write_section and why, with data blocks.
- **WalkEngine:** handles the start, confirm, needs-data, sections, why and done steps, plus explore and stop, re-walk, error and retry, and `run_walk` for U7.
- **WalkLogger:** writes only allow-listed fields to the log.

**`brahma.server`:**
- the local FastAPI app (C8 core routes, SSE walk, map, node detail, history and export, health)
- a signed session cookie
- the tab lock, via the `X-Brahma-Tab` header
- C7 feature mounting, with the profile set by the server
- start command: `python -m brahma.server`

## Files

- **Created:**
  - `src/brahma/agent/` (12 modules)
  - `src/brahma/server/` (14 modules)
  - `tests/agent/` with recorded fixtures for the demo, wrong-dose and urology cases
  - `tests/server/`
  - `README.md`
- **Modified:**
  - `pyproject.toml` (adds `uvicorn`)
  - `.env.example`
  - `.github/workflows/ci.yml`
- **U2 changes:**
  - `AuditKind` gains `line_rejected` and `explored_not_acted`.
  - `Purpose` gains `write_section` and `why`.
  - `RecordedAdapter` supports a `replies` list matched by text.

## Tests (from the build run)

- `pytest tests/agent tests/server -m "not timing" --cov=...`: 81 passed, 96.3% coverage.
- Full suite: 337 passed, 97% coverage.
- Ruff, Ruff format and `mypy --strict` are clean.
- Server start-up check: `/api/health` responds and returns IBD 1.0 and URO 0.1.
- The demo walk ends with 0 ungrounded lines and reaches Tier 2 entry. The deliberate 120 mg line is rejected and recorded in the audit.

## Deviations

1. **Session cookie:** the signed cookie uses standard-library HMAC, because `itsdangerous` isn't installed.
2. **Error format:** errors use `{"error": {...}}`, the same shape as U5.
3. **Tab lock:** taken from the `X-Brahma-Tab` header, and also required for messages, patient changes and form drafts.
4. **Health check:** `/api/health` is public.
5. **Guard additions:**
   - `allowed_node_ids`, which gives `node_not_walked` for nodes the walk didn't choose
   - an `error` field on CheckResult
   - `check_line_by_source` reuses the guard's own matching for per-kg doses
6. **Walk flow:** sections are written after every needs-data round. Re-walk records the previous version in the `done` event and in the walk row. There is an extra `lane_closed` event.
7. **Not done:** node detail always returns `edited: null`, and the server doesn't start U5's background checker (cut list).

## Demo Risks

- **Strict guard:** a live model line that repeats the patient's own values (for example "Hb 10.2 g/dL") will be rejected. The prompt tells the model not to, but a live run could still show more than 0 ungrounded lines. Rehearse this on the real model.
- **Mesalamine dose:** the pack stores mesalamine as exactly 2 g, so a line saying "2.4 g" fails. The severe demo case never reaches that node.
- **Stool culture:** no edge uses the stool culture result, so infectious colitis can only be reached through explore.
- **Shared database connection:** one SQLite connection is shared across threads with no lock. That's fine for a single-user demo.
