# Code Summary — u5-knowledge-updates

## Built

`brahma.updates` adds the following:
- **Proposals:** doctor proposals with a before-and-after view.
- **Publish and reject:** done by the reviewer and written to the audit. Publishing creates a new pack version and retries once if the base moved.
- **Version history:** merges live and superseded versions with proposed and rejected ones.
- **SafeFetcher:** http(s) only, public addresses only (redirects are checked), 10 MB and 20 s caps.
- **Copy check:** a 26-word copy check blocks publishing.
- **Drafting:** drafting from a source through C4, with the source passed as a data block and a strict schema.
- **Source checker:** `python -m brahma.updates.check`, plus an interval set by `BRAHMA_SOURCE_CHECK_HOURS`.
- **Knowledge API:** a C9 FastAPI router (`brahma.updates.api`, feature `knowledge`).

## Files

- **Created:**
  - `src/brahma/updates/` (11 modules)
  - `tests/updates/` (6 test files, conftest, recorded `draft_proposal` fixture)
- **Modified:**
  - `pyproject.toml`: adds `fastapi`
  - `.github/workflows/ci.yml`
  - `.env.example`: adds `BRAHMA_SOURCE_CHECK_HOURS`
  - `src/brahma/platform/models/schemas.py`: adds the purpose `draft_proposal`

## Tests (from the build run)

- `pytest tests/updates --cov=brahma.updates`: 61 passed, 96% coverage.
- Full suite: 254 passed, 97.2% coverage.
- Ruff, Ruff format and `mypy --strict`: clean.

## Deviations

1. **U2 change:** U2's `Purpose` gains `draft_proposal`.
2. **New error:** `ProposalInvalid` (422).
3. **API beyond C9:**
   - `POST /proposals/draft`.
   - Document upload is not built; URLs only.
   - A missing profile header returns 401, and a busy pack returns 503.
   - Errors are mapped through a custom route class.
4. **Audit:** proposals write `proposal_created`. Scheduled proposals use the `system` proposer and are traced by the check-run row.
5. **Publish and audit:** publishing and its audit entry are written one after the other, not in one transaction.
6. **Known limit:** a DNS answer that changes between the address check and the connect isn't caught. This is documented in `fetch.py`.
7. **Drafting prompt:** the prompt holds at most 60,000 characters of the source. The copy check still uses the whole source.
