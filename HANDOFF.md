# Brahma: handoff for the next coding agent

Last updated: Wed Nov 4, 2026, by Muse Code. Read this first, then `README.md`.
Branch `main` is pushed to `github.com/barnikbh/brahma` and in sync with it.

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

The product runs end to end. 465 backend tests (97% coverage) and 104 web tests (93% lines) pass. Ruff, `mypy --strict`, ESLint, Prettier and the build are clean. Two Playwright tests pass against the recorded provider (demo walk incl. traverse choice + follow-up over Enter, and day-3 review). The Knowledge screen rebuild and the live Meta walk are covered by live rehearsal, not e2e.

### Right now (Nov 4, submission day)

- **HEAD:** `main`, pushed and in sync with `github.com/barnikbh/brahma`. Last feature commit is `cf57ad3` (day-3 review walk); the Nov 3–4 traversal/review series is all on `main`.
- **Deadline:** today, Nov 4, 9 PM ET. Critical path: fresh server → `scripts/live_rehearsal.py` → tag the record commit → record → submit. Zero commits after the tag until the video is submitted.
- **Live server:** the owner tests at `http://127.0.0.1:8000` on this machine. Any agent-owned server dies with its session, so if the port answers stale code (or nothing), kill the holder and start fresh: `set -a && source .env && set +a && .venv/bin/python -m brahma.server`. The app is served from `web/dist` (gitignored): rebuild after any web change.
- **Local-only files (NOT in git, a fresh clone lacks them):** `web/index.html` has a 1-line favicon link and `web/public/stethoscope.svg` is its target — a pair, commit together or not at all. Also untracked: `.DS_Store` files everywhere, the AI-DLC audit shard under `aidlc/spaces/default/intents/261029-clinical-decision-graph/audit/`, and gitignored `data/*.db` / `*.log` (the owner's demo case `BR-495233` lives in the local DB).
- **Do not demo or claim:** anything "pending review" in content gaps; symptom-asserted branching beyond the one N90→N96 display link; CI on runners (workflow exists, never verified).

| Unit | What | Status |
|---|---|---|
| U1 `src/brahma/knowledge/` | Graph model, loader, versions, claim matching | Done |
| U2 `src/brahma/platform/` | Append-only audit and PDF export, demo profiles, model gateway (Meta, Claude, hosted Llama, recorded) | Done |
| U3 `src/brahma/cases/` | Patients, cases, finding checks, tab lock, dose and safety checks, treatment edits | Done |
| U4 `src/brahma/agent/`, `src/brahma/server/` | Grounding guard, deterministic graph walk, follow-up turn, FastAPI server with SSE | Done |
| U5 `src/brahma/updates/` | Proposals, reviewer publish, safe URL fetch, copy check, conversational knowledge updates, browse | Done |
| U8 `web/` | React app: sign-in, patients, workspace, map, node panel, history, knowledge | Done |
| U6 prescriptions and follow-up visits | | **Cut** by the owner (Oct 30) |
| U7 benchmark (lean 12-case version, Pass Oct 31) | | **Done** (see Open deadlines) |

Recent additions (all done, tested):
- **Follow-up turn:** after an answered walk, the doctor types treatment history ("Remicade failed. steroids work."). It is extracted, brands are mapped to generics through pack synonyms, and a cited next step is suggested. There is no button. Prior drugs show as "↺ Tried" on the map.
- **IBD pack v1.1:** adds UC after anti-TNF failure (check trough level, then ustekinumab, vedolizumab or tofacitinib; steroids only as a bridge; colectomy review if steroid-refractory).
- **Map labels:** "→ Suggested", "▶ Start here", "✓ Matched", "✓ Result in", never "Done" for plan steps.
- **Patients page** lists recent patients on open.
- **Knowledge screen** has a Browse tab (free exploration of nodes and edges) and an Update tab (free text and source URLs, one model call per node, follow-up questions, "updated by who and when"). A reviewer still publishes.
- **Pathway traversal (Nov 3):** offered drugs render as grey ○ Option boxes and tier-sourced monitoring/watch-outs plus escalation tiers as grey planned steps. The doctor opens an option (dose/safety first) and presses "Choose this option" in the node panel: `POST /api/cases/{id}/traverse` records an append-only choice plus a `traverse_choice` audit event (no model call) and re-lights the map — chosen drug ✓ Chosen, its tier's monitoring blue, siblings grey. Re-choosing moves the highlight. History replay shows the recorded choice (session replay now reads the walk's stored map instead of rebuilding all-used). Follow-up (Nov 4): choosing shows a cited "Now on" next-step card (dose, day-3 review, monitor, watch-for, next tier, follow-up hint; deterministic, no model call); the panel explains when choosing must wait for the walk and shows path context ("Option of / During / Next tier after"). Day-3 review (Nov 4): wired response criteria show "If met → tier" from the pack's escalation conditions, and the panel's "Record day-3 result" form records the value as a review-scoped fact — a presenting value can never skip a tier. A met criterion opens the next tier as a new `review` walk (audited `review_recorded`, `reviewed` SSE event); an unmet one keeps the tier standing with no new walk. Toxic megacolon → Emergency colectomy triggers is an owner-authored display-only branch link (Nov 4, absorb as a real pack edge in v1.2); full symptom-asserted branching still needs clinician-authored branch content (post-submission).
- **Care loop (Nov 4):** the map is a loop, not a column pipeline. Node *kinds* (derived from type in `knowledge/models.py:node_kind`): state purple, observation amber, test blue, action teal, escalation coral. Pack 1.2 adds the `requires` edge (action to test, `strength` must/should, optional `validForDays`) and `if_present` (observation to next step), an optional node `pos`, two tests (IBD-N110 latent TB screen, IBD-N111 hepatitis B screen, source IBD-S15), `requires` from infliximab, ustekinumab, vedolizumab and tofacitinib to both, and `if_present` N90 (toxic megacolon) to N96 and N94 (exclude infection) to N20 (stool tests). The validator checks the shapes (`PackValidator._check_care_edge`). Urology 0.1 loads unchanged (the format is backward compatible; kinds come from node types). Events: the case is a timeline in `ag_care_event` (append-only; kinds `present`, `result`, `done`; a result carries the action it was recorded for). `agent/frontier.py:apply_events` recomputes the lit map after each event, deterministically: chosen action's tests are **To do first** until a result is recorded *for that action*, its monitoring/criteria **Due** then **Done**, watch-outs **Watch for**, a present sign becomes **Present** and its `if_present` targets light (**Now** for an escalation, **Due** for a test, which is Done again after a newer result). API: `POST /api/cases/{id}/events` (map, `lit` nodes, notice; audit kind `care_event`) and `POST /api/cases/{id}/events/card` (the model writes one card from only the newly lit nodes, every line through the grounding guard; the web calls it right after an event or a choice). The map payload carries `timeline`; `GET .../map` always overlays events, so reload and replay keep the lit state. Web: free layout (`web/src/lib/mapLayout.ts`, layers plus relaxation), focus view with a "show whole map" toggle (history replay starts on the whole map), timeline strip, status words Now / To do first / Due / Watch for / Present / Option / Chosen / Tried / Done (planned steps read "Later", never "Suggested"), and panel buttons "Patient has this now", "Record result" and "Mark done" next to "Choose this option"; a click on a block only opens the panel. Logic review (Nov 4, after the owner saw infliximab trough level hanging off the tier): drug-specific monitoring and watch-outs now hang off the drug (N53 to N72, N58 to N103) and light only when that drug is chosen (`Traversal.drug_downstream`); acute severe UC risks (N90, N91, N96) hang off N34 and show Watch for from admission; the tier links to the N92 screening note were removed. Focus view keeps every test with a result and the patient-state path. Layers never wrap (a wrapped stack drew an edge through another node). History (Nov 4, owner bug report): a new walk on the case (day-3 review, follow-up, re-walk on the same version) used to drop the earlier nodes. `views.with_history` now merges earlier walks of the same version into each map (on save and on read): the old entry tier reads Done, the drug chosen then Tried, untaken options Not taken; results recorded earlier stay Done. Focus view hides only what never happened (Not taken, Later) unless it touches something current. The chat button is "Re-walk on the latest knowledge base". Knowledge update and the care loop (Nov 4): a drug added by the update flow copies its neighbour drug's `requires` links (the screens) but never its other outgoing links; `DrugFields` gained an optional `inductionDoseValue`/`inductionDoseUnit` (both or neither; `doseValue` stays the maintenance dose), the matcher grounds a dose claim on it, and the node prompt tells the model to use it. A live dry run on `muse-spark-1.3` (adding a new biologic from a UK SmPC page on eMC) drafted induction and maintenance doses into their own fields, grounded its line (0 rejected) and lit both screens on choice; that drug was then removed so the owner can add it live in the demo (the IBD pack in git is 1.2 with no such node). Version 1.2 is now live, so old local databases keep cases on 1.1 (no screens) until re-walked. Tests: `tests/agent/test_care_events.py`, API test, `GraphCanvas`/`NodePanel`/`Workspace` web tests, e2e extended (choose Vedolizumab, record TB screen). Cases T17 and T18 in `scripts/seed_test_cases.py` / `docs/test-cases.md` / `scripts/live_test_cases.py`; both passed live on `muse-spark-1.3` (card grounded, 0 rejected). The e2e port can be moved with `E2E_PORT=8010 npm run e2e` when 8000 is busy.
- **Benchmark re-run on the care-loop pack after the logic review (Nov 4, IBD 1.2, `muse-spark-1.3`): Pass.** IBD graph 98.6% grounded / 99.3% pathway agreement vs plain model 41.3% / 31.3%; URO graph 100% / 100% vs plain 50% / 50%. Report in `results/benchmark.html`.
- **Criterion "If met" links (Nov 4):** response-criterion panels show where a met threshold leads (day-3 stool/CRP → Tier 3), derived only from exact criterion-field↔escalate-condition matches in the pack (`KnowledgeService.criterion_targets`, `leadsTo` on node detail). Measurements, watch-outs, escalation nodes and unwired criteria (all calprotectin criteria, all Crohn's branches) link nowhere: no matching conditions exist. Acting on a met criterion is now built via the day-3 review walk (see the traversal bullet): review-scoped facts only, so a presenting CRP 60 still never skips Tier 2.

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
- `content/ibd.yaml` (v1.2), `content/urology.yaml` (v0.1). On start-up the server loads any pack file with a version **newer than the live one** as a new live version; older versions are kept so past sessions replay on the version they used.
- `web/` — Vite, React, TypeScript, Tailwind, shadcn/ui, React Flow.
- `tests/` — pytest. Recorded model replies live in `tests/*/fixtures/recorded/` (`replies` with a `match` string, see `RecordedAdapter`).
- `.github/workflows/ci.yml` — backend and web jobs (repo is at `github.com/barnikbh/brahma`; a green CI run on a runner is still unverified).
- `aidlc/` and `.claude/` — the AI-DLC workflow record (requirements, stories, designs, contracts, per-unit plans and summaries) for Claude Code. It is **optional reading** for another agent. Best entry points: `aidlc/spaces/default/intents/261029-clinical-decision-graph/inception/requirements-analysis/requirements.md` (FR/NFR), `.../contract-design/contract-summary.md` (C1–C11 interfaces), `.../delivery-planning/bolt-plan.md` (plan and backlog).
- The AI-DLC workflow is **parked at Build and Test** (`/aidlc --resume` in Claude Code). Skipped units: U6 and U7.

## Known issues and risks

1. **Shared SQLite connection, no lock.** One connection is shared across FastAPI worker threads (`check_same_thread=False`). Overlapping requests can raise a 500 (seen once in testing). The web app works around it (the tab-lock heartbeat starts after the case loads and skips while a request is in flight). **Real fix:** a lock around DB use or a connection per request. Do this before recording the video.
2. **Strict grounding guard vs live models.** Rehearsed Oct 31 on `muse-spark-1.3`: the full demo walk answers with **0 ungrounded** (31 lines cited, ~75 s). It took two fixes (guard matching untouched): `normalize_declared` in `src/brahma/agent/scanner.py` parses declared values ("100 mg", "Tier 2") the way the text scanner does, and the writer prompts gained a claim-shape rule, two few-shot examples and a why-section co-cite rule. Re-run the scripted walk (`scripts/live_rehearsal.py`) after any prompt/model change. Before recording, start a FRESH server: a stale process on port 8000 silently serves old code (bit us once — three "tuning" runs hit a stale server).
3. **Follow-up turn and Knowledge conversation: live-tested Oct 31.** Follow-up maps Remicade→infliximab and answers with 0–1 ungrounded; the knowledge ask→draft→publish loop works end to end (drafted IBD-N58+N103 from Wikipedia, no copy flags, reviewer published IBD 1.2 on a scratch DB). One fix: the interpret prompt now says URLs are fetched automatically (it used to beg for pasted text and leaked the `<source_data>` tag name). fda.gov's abuse-detection blocks the fetcher's transparent user agent (302 to a broken apology page) — the assistant says "could not read" gracefully; deliberately not spoofing a browser UA.
4. **Composer Enter key: fixed Oct 31.** The node panel re-focused its heading on *every* detail load, so a late-resolving detail yanked focus out of the composer between fill and Enter (clicking Send is focus-independent, which is why only Enter failed). The panel now focuses once on open (it remounts per node). Covered by a focus-steal component test plus an Enter follow-up test; the e2e follow-up now presses Enter and passes.
5. **"✎ edited" marker: fixed Oct 31.** Node detail now returns the case's latest stored edit (`CaseService.latest_edit`) when `caseId` is given, and the panel falls back to it when no in-memory outcome exists. Dose/safety already reflected edits server-side, so the reloaded view is exact.
6. **Old cases: non-issue, verified Oct 31.** No IBD 1.0 cases exist locally (all are 1.1+); the banner logic is covered by `test_case_view_shows_the_newer_version_banner`. Still: record with fresh patients.
7. **Map density: accepted, no code.** 12 Monitor-column nodes shrink on fit (minZoom 0.2, React Flow's own zoom/pan controls present and verified). Zoom in while recording.
8. **Not built — all four confirmed correctly unbuilt Oct 31:** form-draft *restore* in the web UI (API + `formDrafts` done and tested; restore is backlog, demo fills forms in one go); zoom slider (React Flow's own controls suffice); first-run tour (cut by owner); background source checker (structurally off — no server wiring, only the `python -m brahma.updates.check` CLI — and its 24 h interval cannot help a demo).
9. **Repo on GitHub: done Nov 4.** `github.com/barnikbh/brahma`, branch `main`, pushed and in sync. `.env` and `data/` stay ignored (`.gitignore` covers them) and `scripts/check_secrets.py` passes. Still to do: tag the commit the demo video is recorded from; no commits after the tag until the video is submitted.
10. Leftover local files `data/*.db`, `data/*.log` are gitignored.
11. **Knowledge ask-loop: fixed.** Impossible requests (new pack, "find your own sources") repeated the same questions to 5 rounds, because the flow can only edit existing nodes from doctor-pasted URLs and the prompt's only move for missing info was to ask. The interpret prompt now states the real limits, and `send()` stops at round 2 when a message adds no URL, node ID or number — with an explanatory message naming the limits. Verified live with the exact transcript.

12. **Knowledge update rebuilt source-first (Nov 1).** The old flow decided what to ask *before* fetching the URL and could not add nodes, so it asked what the page already said. Now: fetch first, then the model decides add or update with the page in hand; an added node takes its neighbour's type, column and incoming links (tier `drugNodeIds` too); the page becomes a pack source cited by the node; a malformed draft is retried once with the reason; a question already asked is never repeated (the thread stops and says why). Every number in a draft must be on the page. Live-checked on `muse-spark-1.3` with the Medscape ustekinumab page: 9 of 9 consecutive drafts after the fixes, about 12 s each. The screen is now a source box, a short note and one review card with Approve and publish (reviewer only).
13. **New `weight_band` dose basis (Nov 1).** `DrugFields.doseBands` holds fixed doses per weight range and must cover every weight. `compute_dose` picks the band. The guard is stricter for these: once the case's weight is known only that patient's band is grounded, and the writer only sees that band. After publishing IBD-N104 on a scratch DB the full walk and follow-up gave 0 ungrounded. A doctor can no longer edit `doseValue` on such a drug without first changing its dose basis.
14. **Day-3 review fixes (Nov 4, Claude).** Review of Muse Code's `cf57ad3`: (a) the review walk dropped treatment history, so after "Remicade failed" a day-3 CRP of 60 re-offered infliximab; it now carries `history`/`base_history`, and a follow-up after a review keeps it. (b) `nan`, `inf` and negative review values were recorded; now refused as `invalid_request`. (c) The unmet message claimed "still responding" from one measure; it now says only that the value does not meet the criterion and the plan is unchanged. Regression tests in `tests/server/test_api.py`. Still open: recording a review starts a new walk, so an earlier "Choose this option" mark is not carried over; `BRANCH_LINKS` in `server/routes/nodes.py` is uncited content outside the pack (move into IBD v1.2 with a source).

## Content gaps (clinical content is unverified, needs a human reviewer)

The owner planned for a family or friend reviewer to check the IBD content **by Oct 31**. Drafted by Claude; every clinical value is unverified.
- **Missing in the IBD pack:** metric plausible ranges (so "confirm range" never triggers), a penicillin-class drug (allergy-conflict path untested on real content), any drug with a pregnancy contraindication, dose rounding rules, and interaction nodes beyond levothyroxine with calcium or iron. Most drugs therefore show "? Not checked" for interactions, which is the intended honest behaviour.
- **Mesalamine** is stored as exactly 2 g, so any line saying 2.4 g or 3 g fails the guard. The severe demo case doesn't reach it. Decide on a dose range before the demo.
- **No edge uses the stool culture result**, so a positive culture doesn't lead to infectious colitis (reachable only via Explore).
- **Ustekinumab induction is not in the pack file.** `IBD-N54` in `content/ibd.yaml` still says "about 6 mg per kg" and has no band node; the update flow adds one to the database only, so a fresh `data/` starts without it. Medscape states 260 / 390 / 520 mg IV by weight (≤55, >55 to 85, >85 kg), which the reviewer should confirm before it goes into the pack.
- **New in v1.1 for the reviewer to verify:** vedolizumab 300 mg IV at weeks 0, 2, 6 then every 8 weeks; tofacitinib 10 mg orally twice daily for 8 weeks then 5 mg twice daily, with the VTE and cardiovascular warning at age 50+ with risk factors and shingles vaccination; ustekinumab about 6 mg/kg IV once then 90 mg SC every 8 weeks (reused from the Crohn's node, confirm for UC); trough level at least 5 µg/mL; steroids only as a bridge; early surgical review if steroid-refractory.
- **Source `IBD-S20`** (FDA 2021 JAK inhibitor safety communication): URL verified Oct 31 — resolves (HTTP 200, correct document). Only the in-app fetcher is blocked by fda.gov's abuse-detection (see issue 3); the citation itself is fine to display.

## Open deadlines and decisions (from the owner)

- **Oct 30 (overdue if not done):** confirm the hackathon rules allow Claude-drafted knowledge content. If not, redraft the pack through the Meta model using the knowledge-update flow before the final run.
- **Oct 31:** reviewer check of the IBD content (above).
- **Nov 2, 9 PM ET:** Meta credentials. The key now works (`muse-spark-1.3`), so the Meta path is confirmed; record this against requirement FR13.10.
- **Nov 3–4:** rehearse the demo on the Meta model, record the video from a tagged commit, submit repo and video before **Nov 4, 9 PM ET**. Ungrounded runs 0–1 per walk and the badge is demo-visible, so record multiple takes and ship a 0-take.
- **Benchmark (U7): DONE Oct 31 (lean 12-case version).** Owner said "do it all", so the shelved 20-case plan became 5 UC + 5 CD + 2 URO (shown, not counted) in `results/benchmark_cases.json`, run live on `muse-spark-1.3` via `scripts/run_benchmark.py` (judge in `src/brahma/bench.py`). Verdict **Pass**: IBD graph 99.3% grounded / 100% pathway agreement vs plain model 48% / 28%; URO graph 93% / 100% vs plain 33% / 50%. Report: `results/benchmark.html`. Expected pathways are derived from `walk_graph`, never hand-written. Note: `uc-stool-positive` was replaced by `uc-day3-responder` because no edge gates on stool culture (see content gaps) — the positive result changed nothing, so the case discriminated only in the plain arm.
- **Review prep + recording guide (added Oct 31):** `docs/review-checklist.md` (dose table, thresholds, 4 pack-design questions for the reviewer, expected pathways, sign-off via `reviewedBy`) and `docs/recording-guide.md` (10-step demo script incl. the day-3 review beat, takes/recovery, submission checklist).

## Backlog (low priority, not scheduled)

- **Care-graph redesign: built Nov 4 (owner moved it before submission). See "Care loop" under Recent additions.** Left for later: the pack-authored `pos` layout is supported but no positions are authored (auto layout is used), `valid_for_days` is supported but unused (TB/hepatitis B screens must be recorded per treatment), monitoring does not come due again on its interval, and positive screen results do not lead anywhere yet (needs a reviewer-authored edge).

- **Personal versions of the knowledge graph (added Oct 31):** a doctor's update stays with that doctor, like a simple branch. Brahma starts from the global version, applies the update and saves it as that doctor's version; a reviewer publishes it to make it global. No screen is planned. Today a published change is global at once.
- U6 prescriptions and follow-up visits, the first-run tour, form drafts, the background source checker, "edited" marker persistence.

## Owner preferences

- Move fast toward a working demo. Skip ceremony and fine-grained process choices; pick a sensible default and say what you chose.
- **Save tokens:** short replies, cheap models for build subagents, small fixes done directly, no extra reviews or documents.
- Never put keys in chat. Tell the owner the file path and let them paste secrets themselves.
- The owner is not deeply technical; explain simply and give copy-paste commands.
