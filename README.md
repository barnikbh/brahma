# Brahma

**Decision support, not diagnosis.** Brahma walks a synthetic patient case through a
cited clinical knowledge graph and shows only lines that trace to a graph node and its
source. It works on synthetic cases only, never on real patient data, and it makes no
claim of HIPAA compliance or any certification.

## Run the backend

The backend runs locally only. There is no hosted URL.

### Prerequisites

- Python 3.12 or later.
- For a real walk: an API key for one model provider (the Meta Model API for the
  submitted demo; Claude or a free hosted Llama tier while building). The `recorded`
  provider needs no key and replays recorded test replies.

### Install

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### Configure

Copy `.env.example` to `.env` (git-ignored) and fill in the values for your provider.
Never commit real values. The server reads:

| Variable | Meaning |
|---|---|
| `BRAHMA_MODEL_PROVIDER`, `BRAHMA_MODEL_NAME` and the provider's key | The model (see `.env.example`). |
| `BRAHMA_SESSION_SECRET` | Signs the session cookie. Required unless the provider is `recorded`. |
| `BRAHMA_DB_PATH` | SQLite file; default `./data/brahma.db`. |
| `BRAHMA_FEATURE_MODULES` | Feature modules to mount; default `brahma.updates.api`. |
| `BRAHMA_LOG_PATH` | Walk log (JSON lines, no clinical text); default `./data/brahma.log`. |
| `BRAHMA_HOST`, `BRAHMA_PORT` | Bind address; default `127.0.0.1:8000`. |
| `BRAHMA_RECORDED_DIR` | Optional fixture folder for the `recorded` provider (the demo replies are in `tests/agent/fixtures/recorded/demo`). |

### Start

```bash
set -a; . ./.env; set +a
.venv/bin/python -m brahma.server
```

On the first start the server loads the packs in `content/` (IBD and the urology stub)
and seeds the demo profiles. Check it with:

```bash
curl http://127.0.0.1:8000/api/health
```

The API is under `/api` (profiles, session, patients and cases, the walk as
Server-Sent Events, node detail, history and export). The knowledge-update screens are
mounted under `/api/knowledge`.

## Run the app

The doctor web app lives in `web/` (Vite, React and TypeScript). It needs Node 20 or
later. Build it once, then the backend serves it, so the whole app runs from one command
on one URL:

```bash
cd web && npm ci && npm run build && cd ..
.venv/bin/python -m brahma.server
```

Open http://127.0.0.1:8000, pick a demo profile (Dr. Maya), accept the disclaimer and
create a synthetic patient. To walk the recorded demo case without a model key, start the
server with the recorded demo replies:

```bash
BRAHMA_MODEL_PROVIDER=recorded BRAHMA_RECORDED_DIR=tests/agent/fixtures/recorded/demo \
  .venv/bin/python -m brahma.server
```

and type: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`.

On the Knowledge screen, Browse walks the saved nodes. Update takes a source website and a short note: Brahma reads the page, drafts the node change (updating a node, or adding one beside it), cites the page and shows a before and after for a reviewer to approve. In demo mode the page `https://reference.medscape.com/drug/stelara-wezlana-ustekinumab-345050` gives a recorded draft (the page itself is still fetched, so this one step needs network), and a note with no URL shows the canned follow-up question.

For frontend work, `cd web && npm run dev` starts Vite on http://127.0.0.1:5173 and sends
`/api` to the backend on port 8000.

Web checks (run from `web/`):

```bash
npm run lint && npm run typecheck && npx prettier --check .
npm run test -- --coverage   # Vitest, 80% line floor
npm run build
npx playwright install chromium   # once
npm run e2e                      # demo walk + day-3 review (starts the server itself)
```

### Backend tests

```bash
.venv/bin/python -m pytest tests -m "not timing" --cov=brahma --cov-fail-under=80
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy --strict src/brahma
```

Tests use the recorded provider and temporary databases: no network and no keys.
