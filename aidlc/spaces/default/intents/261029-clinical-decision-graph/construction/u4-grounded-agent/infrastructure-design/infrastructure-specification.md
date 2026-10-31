# Infrastructure Specification — u4-grounded-agent

Upstream: `performance-design.md`, `security-design.md`, `scalability-design.md`, `reliability-design.md`, `observability-design.md`, `logical-components.md`, `functional-spec.md` (U4), `components.md` (BackendServer), and `contract-summary.md` (C7, C8).

This runs locally only. There is no cloud infrastructure and no hosting, which follows the team practice.

- **Process:** `python -m brahma.server` starts uvicorn, which serves the FastAPI app on `127.0.0.1:8000`. It is a single process.
- **Storage:** one SQLite file at `BRAHMA_DB_PATH`, default `data/brahma.db`. The `data/` folder is gitignored.
- **Configuration (environment variables):**
  - `BRAHMA_SESSION_SECRET`
  - `BRAHMA_FEATURE_MODULES`, default `brahma.updates.api`
  - `BRAHMA_LOG_PATH`
  - `BRAHMA_HOST` and `BRAHMA_PORT`
  - the U2 model variables

  All of these are listed in `.env.example` with empty values.
- **Start-up:**
  1. Open the database.
  2. Load the packs from `content/*.yaml` if none are loaded yet. This is FR2.6: the initial pack is loaded directly.
  3. Seed the profiles.
  4. Mount the feature modules.
- **Cost:** none. The only spend is on model provider calls.
