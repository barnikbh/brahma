# Brahma: handoff for the next coding agent

Last updated: Sat Oct 31, 2026, by Claude. Read this first, then `README.md`.

## What this is

**Brahma** is a clinical decision graph for doctors: a knowledge graph, a grounded agent that walks it, an audit trail, a web app (chat plus map) and a knowledge-update flow. It is decision support, not diagnosis.

- **Hackathon:** Meta Global AI Developer Hackathon, Theme 2, Indie track.
- **Deadline:** Wed **Nov 4, 2026, 9:00 PM ET**. The submission is a **public GitHub repo plus a demo video**. There is no hosted URL: the app runs locally.
- **Content:** IBD (ulcerative colitis and Crohn's at full depth) plus a small urology pack. The demo model must be a **Meta model through the Meta Model API**. Claude was used only for building and for drafting knowledge content.

Hard rules, never break these:
- Synthetic or de-identified data only. Never real patient data or an EHR.
- Say "Decision support, not diagnosis". Never claim HIPAA compliance or any certification.
- Every answer line must be grounded in a cited knowledge-graph node. The grounding check can never be weakened to make something pass.
- Paraphrase guideline content. Never copy it verbatim into nodes.
- Secrets only in environment variables or `.env` (gitignored). Never commit keys, and never paste a key into chat or logs.
- No plaintext `data/*.json`.

## Where things stand

The product runs end to end. 371 backend tests (97% coverage) and 80 web tests (93%) pass. Ruff, `mypy --strict`, ESLint, Prettier and the build are clean. A Playwright demo-walk test passes against the recorded provider. The follow-up turn, the Knowledge screen rebuild and the live Meta walk were not all covered by that e2e (see Known issues).

| Unit | What | Status |
|---|---|---|
| U1 `src/brahma/knowledge/` | Graph model, loader, versions, claim matching | Done |
| U2 `src/brahma/platform/` | Append-only audit and PDF export, demo profiles, model gateway (Meta, Claude, hosted Llama, recorded) | Done |
| U3 `src/brahma/cases/` | Patients, cases, finding checks, tab lock, dose and safety checks, treatment edits | Done |
| U4 `src/brahma/agent/`, `src/brahma/server/` | Grounding guard, deterministic graph walk, follow-up turn, FastAPI server with SSE | Done |
| U5 `src/brahma/updates/` | Proposals, reviewer publish, safe URL fetch, copy check, conversational knowledge updates, browse | Done |
| U8 `web/` | React app: sign-in, patients, workspace, map, node panel, history, knowledge | Done |
| U6 prescriptions and follow-up visits | | **Cut** by the owner (Oct 30) |
| U7 benchmark (20 cases, graph vs plain model) | | **Cut for now** |

Recent additions (all done, tested):
- **Follow-up turn:** after an answered walk, the doctor types treatment history ("Remicade failed. steroids work."). It is extracted, brands are mapped to generics through pack synonyms, and a cited next step is suggested. There is no button. Prior drugs show as "↺ Tried" on the map.
- **IBD pack v1.1:** adds UC after anti-TNF failure (check trough level, then ustekinumab, vedolizumab or tofacitinib; steroids only as a bridge; colectomy review if steroid-refractory).
- **Map labels:** "→ Suggested", "▶ Start here", "✓ Matched", "✓ Result in", never "Done" for plan steps.
- **Patients page** lists recent patients on open.
- **Knowledge screen** has a Browse tab (free exploration of nodes and edges) and an Update tab (free text and source URLs, one model call per node, follow-up questions, "updated by who and when"). A reviewer still publishes.

## Run it

Setup once: Python 3.12+ in `.venv`, Node 20+.

```bash
.venv/bin/pip install -e ".[dev]"
cd web && npm ci && npm run build && cd ..
```

**Real Meta model.** `.env` at the project root (gitignored) needs these keys; the owner has already filled it in:

```
BRAHMA_MODEL_PROVIDER=meta
BRAHMA_MODEL_NAME=muse-spark-1.3
BRAHMA_MODEL_BASE_URL=https://api.meta.ai/v1
META_API_KEY=...            # never print or commit
BRAHMA_SESSION_SECRET=...   # required with a real provider
```

```bash
set -a && source .env && set +a && .venv/bin/python -m brahma.server
```

Open http://127.0.0.1:8000. The server reads environment variables only, not `.env` itself, so source it first. Restart after any backend change. The web app is served from `web/dist`, so run `npm run build` after any web change and hard-refresh.

**Recorded demo (no key, offline):**

```bash
BRAHMA_MODEL_PROVIDER=recorded BRAHMA_RECORDED_DIR=tests/agent/fixtures/recorded/demo .venv/bin/python -m brahma.server
```

Then use the demo text: `34-year-old woman, bloody stool 6 months, Hb 10.2 g/dL, calprotectin 850 µg/g`. Recorded mode replies only to these canned inputs; other text gives "model provider gave no usable reply".

**Meta Muse Spark notes.** Muse Spark always reasons and the reasoning counts against `max_tokens`. The Meta adapter in `src/brahma/platform/models/adapters.py` therefore sends `reasoning_effort: low` and adds 4,000 tokens of headroom (without this every call came back empty). The standard model is `muse-spark-1.3`. Do not use the `-contributor` variant (Meta trains on inputs). Keys start with `LLM_`. Each walk takes roughly 5 seconds per model step.

Demo walk: sign in as Dr. Maya, accept the disclaimer, create a patient, type the demo text, confirm the findings, answer the two needs-data forms (stool culture, colonoscopy, then extent and severity), read the cited pathway. Then try the follow-up: `Remicade failed. steroids work. Suggest alternate treatment plan` (click **Send**; see Known issues).

## Checks (run all before calling anything done)

```bash
.venv/bin/python -m pytest tests --cov=brahma --cov-fail-under=80 && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy --strict src/brahma
cd web && npm run lint && npm run typecheck && npx prettier --check . && npm run test -- --coverage && npm run build
cd web && npm run e2e     # needs port 8000 free; uses the recorded provider
python scripts/check_env_example.py && python scripts/check_secrets.py
```

## Layout

- `src/brahma/` — Python package as above. Tables share one SQLite file (`data/brahma.db`) with per-unit prefixes: `kg_`, `pf_`, `cs_`, `ag_`, `up_`.
- `content/ibd.yaml` (v1.1), `content/urology.yaml` (v0.1). On start-up the server loads any pack file with a version **newer than the live one** as a new live version; older versions are kept so past sessions replay on the version they used.
- `web/` — Vite, React, TypeScript, Tailwind, shadcn/ui, React Flow.
- `tests/` — pytest. Recorded model replies live in `tests/*/fixtures/recorded/` (`replies` with a `match` string, see `RecordedAdapter`).
- `.github/workflows/ci.yml` — backend and web jobs (never run yet; the repo isn't on GitHub).
- `aidlc/` and `.claude/` — the AI-DLC workflow record (requirements, stories, designs, contracts, per-unit plans and summaries) for Claude Code. It is **optional reading** for another agent. Best entry points: `aidlc/spaces/default/intents/261029-clinical-decision-graph/inception/requirements-analysis/requirements.md` (FR/NFR), `.../contract-design/contract-summary.md` (C1–C11 interfaces), `.../delivery-planning/bolt-plan.md` (plan and backlog).
- The AI-DLC workflow is **parked at Build and Test** (`/aidlc --resume` in Claude Code). Skipped units: U6 and U7.

## Known issues and risks

1. **Shared SQLite connection, no lock.** One connection is shared across FastAPI worker threads (`check_same_thread=False`). Overlapping requests can raise a 500 (seen once in testing). The web app works around it (the tab-lock heartbeat starts after the case loads and skips while a request is in flight). **Real fix:** a lock around DB use or a connection per request. Do this before recording the video.
2. **Strict grounding guard vs live models.** Rehearsed Oct 31 on `muse-spark-1.3`: the full demo walk answers with **0 ungrounded** (31 lines cited, ~75 s). It took two fixes (guard matching untouched): `normalize_declared` in `src/brahma/agent/scanner.py` parses declared values ("100 mg", "Tier 2") the way the text scanner does, and the writer prompts gained a claim-shape rule, two few-shot examples and a why-section co-cite rule. Re-run the scripted walk (`scripts/live_rehearsal.py`) after any prompt/model change. Before recording, start a FRESH server: a stale process on port 8000 silently serves old code (bit us once — three "tuning" runs hit a stale server).
3. **Follow-up turn and Knowledge conversation: live-tested Oct 31.** Follow-up maps Remicade→infliximab and answers with 0–1 ungrounded; the knowledge ask→draft→publish loop works end to end (drafted IBD-N58+N103 from Wikipedia, no copy flags, reviewer published IBD 1.2 on a scratch DB). One fix: the interpret prompt now says URLs are fetched automatically (it used to beg for pasted text and leaked the `<source_data>` tag name). fda.gov's abuse-detection blocks the fetcher's transparent user agent (302 to a broken apology page) — the assistant says "could not read" gracefully; deliberately not spoofing a browser UA.
4. **Composer:** after an answered walk, pressing Enter in the chat box didn't send in the e2e; clicking **Send** works. Cause unknown.
5. **"✎ edited" marker** is kept only in the browser; node detail returns `edited: null`, so it disappears on reload.
6. **Old cases** walked on IBD 1.0 show the "newer version available" banner. Re-walk them, or create new patients, to use the follow-up path.
7. **Map density:** the full IBD map has about 12 nodes in the Monitor column; nodes get small when fitted. Zoom in while recording.
8. **Not built:** form drafts (`PUT .../draft`), a zoom slider (React Flow's own controls are there), the first-run tour (cut as a Could), the background source checker is off in the server.
9. **Repo is not a git repo yet.** Initialise it, make sure `.env` and `data/` stay ignored (`.gitignore` covers them), run `scripts/check_secrets.py`, then create the public GitHub repo. Tag the commit the demo video is recorded from. No commits after the deadline.
10. Leftover local files `data/*.db`, `data/*.log` are gitignored.

## Content gaps (clinical content is unverified, needs a human reviewer)

The owner planned for a family or friend reviewer to check the IBD content **by Oct 31**. Drafted by Claude; every clinical value is unverified.
- **Missing in the IBD pack:** metric plausible ranges (so "confirm range" never triggers), a penicillin-class drug (allergy-conflict path untested on real content), any drug with a pregnancy contraindication, dose rounding rules, and interaction nodes beyond levothyroxine with calcium or iron. Most drugs therefore show "? Not checked" for interactions, which is the intended honest behaviour.
- **Mesalamine** is stored as exactly 2 g, so any line saying 2.4 g or 3 g fails the guard. The severe demo case doesn't reach it. Decide on a dose range before the demo.
- **No edge uses the stool culture result**, so a positive culture doesn't lead to infectious colitis (reachable only via Explore).
- **New in v1.1 for the reviewer to verify:** vedolizumab 300 mg IV at weeks 0, 2, 6 then every 8 weeks; tofacitinib 10 mg orally twice daily for 8 weeks then 5 mg twice daily, with the VTE and cardiovascular warning at age 50+ with risk factors and shingles vaccination; ustekinumab about 6 mg/kg IV once then 90 mg SC every 8 weeks (reused from the Crohn's node, confirm for UC); trough level at least 5 µg/mL; steroids only as a bridge; early surgical review if steroid-refractory.
- **Source `IBD-S20`** (FDA 2021 JAK inhibitor safety communication): URL verified Oct 31 — resolves (HTTP 200, correct document). Only the in-app fetcher is blocked by fda.gov's abuse-detection (see issue 3); the citation itself is fine to display.

## Open deadlines and decisions (from the owner)

- **Oct 30 (overdue if not done):** confirm the hackathon rules allow Claude-drafted knowledge content. If not, redraft the pack through the Meta model using the knowledge-update flow before the final run.
- **Oct 31:** reviewer check of the IBD content (above).
- **Nov 2, 9 PM ET:** Meta credentials. The key now works (`muse-spark-1.3`), so the Meta path is confirmed; record this against requirement FR13.10.
- **Nov 3–4:** rehearse the demo on the Meta model, record the video from a tagged commit, submit repo and video before **Nov 4, 9 PM ET**. Ungrounded runs 0–1 per walk and the badge is demo-visible, so record multiple takes and ship a 0-take.
- **Benchmark (U7):** the owner deferred it. The original plan was a 20-case synthetic benchmark (graph run vs plain model, grounded share at least 95%, graph beats plain). Check the hackathon submission requirements: if a benchmark or quantitative result is expected, rebuild U7 (design in `requirements.md` FR13).

## Backlog (low priority, not scheduled)

- **Personal versions of the knowledge graph (added Oct 31):** a doctor's update stays with that doctor, like a simple branch. Brahma starts from the global version, applies the update and saves it as that doctor's version; a reviewer publishes it to make it global. No screen is planned. Today a published change is global at once.
- U6 prescriptions and follow-up visits, the first-run tour, form drafts, the background source checker, "edited" marker persistence.

## Owner preferences

- Move fast toward a working demo. Skip ceremony and fine-grained process choices; pick a sensible default and say what you chose.
- **Save tokens:** short replies, cheap models for build subagents, small fixes done directly, no extra reviews or documents.
- Never put keys in chat. Tell the owner the file path and let them paste secrets themselves.
- The owner is not deeply technical; explain simply and give copy-paste commands.
