# Code Summary — u1-knowledge-graph

## What Was Built

U1 is the knowledge-graph library: the C1 interface in `src/brahma/knowledge/`, the IBD pack v1.0 (64 nodes, 81 edges, 19 sources) and the urology stub v0.1 (8 nodes, 7 edges, 2 sources). As the first unit, it also adds the project's Python setup and its CI workflow.

## Files

**Modified:**
- `.gitignore`: entries appended after the AI-DLC block for `.venv/`, `data/`, `.env`, `__pycache__/`, tool caches, `.coverage` and `*.egg-info/`. Existing lines are unchanged.

**Created:**
- `pyproject.toml`: package `brahma`, Python 3.12 or later, pydantic, pyyaml, and dev tools. Ruff and mypy are configured here.
- `.github/workflows/ci.yml`: runs on push to `main` with `contents: read`, on Python 3.12. It installs with pip, then runs Ruff, `mypy --strict`, pytest with coverage at 80% or more on `brahma.knowledge`, and pack validation.
- `src/brahma/knowledge/`:

  | File | Purpose |
  |---|---|
  | `errors.py` | Typed errors |
  | `models.py` | Pydantic models with per-type field schemas |
  | `db.py` | `kg_connect`: autocommit, WAL, busy timeout, foreign keys, tables, immutability triggers, one-live index |
  | `loader.py` | Size and extension check, then `NoAliasSafeLoader` |
  | `repository.py` | `BEGIN IMMEDIATE` publish, reads, comments |
  | `validator.py` | Validation rules BR1.1, BR1.2, BR1.4 and BR3.5, plus the patient-data scan with a clinical allow-list |
  | `units.py` | Decimal unit table |
  | `matcher.py` | `match_claims`, `find_supporting_node` |
  | `index.py` | `GraphIndex`, built at load |
  | `service.py` | `KnowledgeService`, the C1 interface, with one JSON log line per load or publish |
  | `validate.py` | Command-line validator |

- `content/ibd.yaml`, `content/urology.yaml`.
- `scripts/check_copy.py`: the verbatim-copy check, which flags runs of more than 25 words.
- `tests/knowledge/`: 7 test files and 8 fixtures.

## How to Run

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest tests/knowledge --cov=brahma.knowledge
.venv/bin/python -m brahma.knowledge.validate content/ibd.yaml content/urology.yaml
```

Python 3.15 on this machine works: every dependency has a wheel for it, so Python 3.12 wasn't needed. CI uses 3.12.

## Test Results (rerun by the orchestrator)

| Check | Result |
|---|---|
| `pytest tests/knowledge --cov=brahma.knowledge` | 83 passed; coverage 98% (floor 80%) |
| Pack validation | Both packs OK |
| `ruff check .` | Passed |
| `mypy --strict src/brahma/knowledge` | No issues in 12 files |
| Timing tests | `search` and `neighbours` under 50 ms on 2,000 nodes; cold call under 50 ms; both packs load under 2 s |

**Not run:** the GitHub Actions workflow itself. The project isn't a git repository yet and nothing has been pushed. Its steps were run locally instead.

## Key Decisions and Deviations From the Plan

1. **Two extra errors:**
   - `BaseNotLive`: `create_version` was given a base that isn't the live version.
   - `VersionNotFound`: a read names an unknown pack or version.
2. **Where the atomic publish lives:** it's `KnowledgeRepository.publish()` (`BEGIN IMMEDIATE`, check live, supersede, insert), and `KnowledgeService` calls it.
3. **Stricter field schemas:**
   - Metric and test nodes accept `synonyms`.
   - Edge IDs carry the pack prefix.
   - Text edge conditions use `eq` and must match one of the test's `resultOptions`.
   - A numeric condition's unit must convert to the metric's unit.
   - A tier's `drugNodeIds` must point at drug nodes.
4. **Sources are stored once per pack.** Reloading a source ID with different details is refused.
5. **CI installs with pip**, not `uv sync --frozen`: there's no uv and no lock file.
6. **Ruff ignores N818**, because the contract names errors without the `Error` suffix. It also skips `.claude`, `aidlc` and `docs`.
7. **`kg_connect` has an optional `busy_timeout_ms`**, so the `PackBusy` test runs quickly. The default is 5000.
8. **`find_supporting_node`** returns None when given no claims, and uses natural ID order.
9. **Reloading a pack whose file has no `changeSummary`** records "Reload". BR1.3 defined only "Initial load".

## Clinical Content for Your Reviewer

Everything is paraphrased and cited to named guidelines (BSG 2019, ECCO, ACG, AGA, NICE DG11, STRIDE-II, WHO 2011, ATA 2014, AUA 2016). Section names are descriptive rather than numbered. **None of it has been checked against the guideline texts yet.** Your reviewer needs to confirm it.

**Doses and schedules:**
- Hydrocortisone 100 mg IV four times daily.
- Methylprednisolone 60 mg IV once daily, assessed on day 3.
- Infliximab 5 mg/kg at weeks 0, 2 and 6, then every 8 weeks.
- Ustekinumab: IV induction of about 6 mg/kg, then 90 mg SC every 8 weeks. The weight bands are not given.
- Budesonide 9 mg once daily.
- Levothyroxine 1.6 µg/kg/day.
- Mesalamine: `doseValue` 2 g, with a range of 2–3 g/day. A claim of 2.4 g will fail the exact match, so this needs a decision.

**Thresholds:**
- Hb below 10.5 g/dL, and six or more stools a day (Truelove and Witts).
- Day 3: more than 8 stools, or CRP above 45 mg/L.
- Calprotectin above 50 µg/g.
- Response target: calprotectin at or below 250 µg/g.
- Infliximab trough level of at least 5 µg/mL.
- WHO Hb lower limits: female 12, pregnant 11, male 13 g/dL.
- Colectomy if there's no improvement within 4–7 days of rescue therapy.
- Urology: ureteric stone of 10 mm or smaller.

**Judgement calls:**
- The levothyroxine and calcium or iron interaction is rated "moderate".
- Contraindications are label-level.

**Left out rather than guessed:**
- All plausible ranges, and the upper limits for Hb.
- The toxic megacolon size threshold.
- Thiopurine, ciclosporin and rectal mesalamine nodes.
- The prednisolone dose and taper.
- Mesalamine induction length.
- Infliximab rounding.
- Tamsulosin dosing. As a result, the urology tier has no drug.
- A Tier 1 path for mild colonic Crohn's disease.
- Tier 1 and calprotectin monitoring intervals.
- An ICD code for infectious colitis.

## Carry-overs

- The urology tier has no drug node, so US9.1's walk ends at a plan with no prescription. That is enough for AC9.1.1.
- Mesalamine's exact-match behaviour (above) affects U4's claim check on the Tier 1 line.
