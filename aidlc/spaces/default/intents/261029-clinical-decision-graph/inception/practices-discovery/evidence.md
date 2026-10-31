# Evidence — Practices Discovery

## Context

- **Project type**: greenfield (workspace scan, `aidlc-state.md`). No application code, no CI or deployment configuration, and the folder is not yet a git repository, so there was no history, branch or tooling to infer practices from.
- **Scope**: `mvp` (scope file `skeleton: on`; `org.md` adds an 80% line-coverage floor and CI before merge). Test Strategy: `Standard`.
- **Participants**: the pipeline-deploy lead, working alone. The collaborators switch is off, so no quality, developer or devsecops contributions exist.
- **Prior baseline**: `memory/team.md` and `memory/project.md` were empty templates. This is the first run.

## Sources Inspected

| Source | What it gave |
|--------|--------------|
| `aidlc/spaces/default/memory/org.md` (five practice sections) | The suggested defaults the draft and interview started from |
| `ideation/intent-capture/intent-statement.md` | Decision-support framing, grounded-answer principle, success metrics, deadline |
| `ideation/feasibility/feasibility-assessment.md` | Meta API access untested (condition 1); hosting not chosen; effort budget |
| `ideation/feasibility/constraint-register.md` | C-T1, C-T3, C-T5, C-O1, C-R1–C-R4 used for `discovered-rules.md` |
| `ideation/scope-definition/scope-document.md` | Milestones (Oct 31 thin slice deployed, Nov 2 feature-complete) |
| Workspace owner rules (`CLAUDE.md`) | Secrets only in environment variables; never commit plaintext `data/*.json` |
| `.claude/knowledge/aidlc-pipeline-deploy-agent/` | Branching, CI/CD and deployment pattern menus |
| `inception/practices-discovery/practices-discovery-questions.md` | The builder's answers Q1–Q10 and the confirmed consolidated summary |

## Interview Decisions

| Q | Area | Decision |
|---|------|----------|
| Q1 | Way of Working | B: commit straight to `main`, no branches |
| Q2 | Walking Skeleton | C: no thin slice first; build features one after another |
| Q3 | Testing Posture | A: test-after; each layer's tests written and run before it is committed |
| Q4 | Testing Posture | A: 80% line coverage measured separately for backend and frontend, plus a browser smoke test |
| Q5 | Deployment | X: run locally; code in a public GitHub repo with clear local setup instructions |
| Q6 | Code Style | A, chosen for the builder at their request: Ruff; ESLint, Prettier, TypeScript strict; checked automatically |
| Q7 | Walking Skeleton / models | X: no Meta credentials yet, so develop with Claude; providers plug-and-play; start with something free; the knowledge tree is built with Claude, but the app can generate it through Meta or other models |
| Q8 | Deployment | A: submission is the public repo plus the demo video; no hosted URL |
| Q9 | Way of Working | A: the submitted demo and the benchmark run on a Meta model; Claude only for building and drafting content |
| Q10 | Way of Working | A: the first free option is Meta's open Llama models on a free hosted tier (e.g. Groq, OpenRouter) |
| Summary | All | Confirmed: "Looks correct" |

## Contradictions Resolved

1. **No slice (Q2) vs. the approved Oct 31 deployed-slice milestone**: resolved by Q7. The milestone is dropped and the dates are re-planned in delivery planning. The early check on Meta API access that the slice provided is replaced by a swappable model provider, so work does not depend on Meta access.
2. **Local-only run (Q5) vs. the approved deliverable "deployed public URL plus demo video" (C-T5)**: resolved by Q8. The deliverable becomes the public repository with local setup instructions plus the demo video. C-T5 is superseded for this intent.
3. **Meta Model API mandate (C-T1) vs. developing with Claude (Q7)**: resolved by Q9. The submitted demo and the benchmark must run on a Meta model; Claude is limited to building and drafting knowledge content. This is recorded as a Mandated rule.
4. **`org.md` Construction default (per-Bolt worktree branch squash-merged into `main`) vs. Q1 (no branches)**: the affirmed `team.md` Way of Working replaces it for this project's Construction work.
5. **`org.md` Deployment default (deploy on merge to staging, manual production gate)**: no environments exist, so it does not apply. Coverage floors and CI before merge are kept; CI runs on every push to `main`.

## Remaining Uncertainty

- Meta Model API credentials have not been obtained yet. The submission rule (Q9) depends on getting them before the demo video is recorded and the benchmark is run.
- It is not confirmed whether the hackathon rules accept knowledge content drafted with Claude, as long as the running product uses a Meta model.
- Downstream updates are needed: the scope document's milestones (Oct 31 slice, deployed URL) and constraint C-T5 are superseded by Q2/Q7/Q8 and must be updated in requirements and delivery planning.
- The free hosted Llama tier (Q10) has rate limits that are not yet known; this may affect running the 20-case benchmark during development.
- The commit hash in the timestamp is `none` until the git repository is created.
