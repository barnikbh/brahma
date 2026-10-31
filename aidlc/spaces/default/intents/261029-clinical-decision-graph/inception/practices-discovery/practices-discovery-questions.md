# Practices Discovery — Questions

Context: greenfield, one builder, six days to the Nov 4 submission. Suggested answers come from the draft in `team-practices.md` (framework defaults sized for this build). Answer the way you'd actually work.

## Q1. [Way of Working] How code is saved and merged

The project folder isn't a git repository yet. How should code be saved and merged?

A. Start a git repo with a private GitHub remote; each piece of work goes on a short-lived branch and is squash-merged into `main`
B. Commit straight to `main`, no branches
C. Feature branches with self-merged pull requests on GitHub
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q2. [Walking Skeleton] Thin slice first

Build a thin end-to-end slice first? A walking skeleton is a minimal version that runs the whole way through, built first to prove the pieces connect before the real features go in.

A. Yes: the Oct 31 slice (sign-in, one question, a real Meta model call, a cited answer from the ulcerative colitis branch with the disclaimer, an audit record) at the public URL
B. Yes, but running locally only; deploy later
C. No: build the features one after another
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q3. [Testing Posture] When tests get written

The plan keeps an 80% line-coverage floor with tests run automatically before merge. When are tests written?

A. Test-after: build each layer, then write and run its tests before merging
B. Test-first (TDD) for the grounding and graph-walk logic; test-after for everything else
C. Demo-case scenarios written first in plain Given/When/Then (BDD), unit tests after
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. [Testing Posture] Where the coverage floor applies

How should the 80% floor and the end-to-end check apply?

A. 80% measured separately for backend and frontend, plus a browser smoke test against the deployed URL
B. 80% on the backend; the frontend gets lighter component tests, plus the browser smoke test
C. 80% on both sides, no browser smoke test
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. [Deployment] How releases go out, and where

How should the app be deployed, and on what hosting?

A. One public environment that deploys on merge to `main` after checks and a smoke test; your merge is the production approval. Hosting: Vercel (frontend) + Render or Railway (Python backend)
B. Same deploy-on-merge, on Fly.io for both (as you use for finance-assistant)
C. Same deploy-on-merge, one container on Render or Railway serving the API and the built frontend
D. Not yet defined
X. Other (please specify)

[Answer]: X (run locally; the code lives in a public GitHub repo with clear instructions for setting it up locally)

## Q6. [Code Style] Formatting and lint tools

Which formatting and lint tools?

A. Ruff (lint and format) for Python; ESLint, Prettier and TypeScript strict mode for the frontend; checked automatically before merge
B. Same as A, plus a pre-commit hook so issues are caught before each commit
C. Black and flake8 for Python; ESLint and Prettier for the frontend
D. Not yet defined
X. Other (please specify)

[Answer]: A (you asked me to decide: Ruff for Python; ESLint, Prettier and TypeScript strict mode for the frontend; checked automatically before merge)

## Q7. [Walking Skeleton] Follow-up: no slice vs. the Oct 31 milestone

You chose to build features one after another (Q2). The approved scope has a thin slice deployed by Oct 31, and Meta model access is still untested; the slice was where an access problem would surface early (scope-document.md, Milestones; feasibility risk R1). Which holds?

A. Keep the Oct 31 milestone as a checkpoint: by then the features built so far are deployed and make a real Meta model call, without a separate slice step
B. Drop the Oct 31 milestone: build features in order, deploy once near Nov 2; accept that an API problem surfaces late
C. Drop the milestone, but make one real Meta model call first thing, before building features
D. Not yet defined
X. Other (please specify)

[Answer]: X ("I don't have the meta APIs. So allow me to test with claude. And meta API and other apis should be easy to plug and play. Something free to begin with? I'll try to get the meta credentials before that. Also we'll build the knowledge tree with claude, but there should be a way in the code to generate it using the meta/alternate APIs in the application")

## Q8. [Deployment] Follow-up: local run vs. the deployed public URL

You chose to run it locally from a public GitHub repo (Q5). The approved feasibility and scope set the deliverable as a deployed public URL plus a demo video (constraint C-T5). Which deliverable holds for the submission?

A. Public repo with clear local setup, plus the demo video; no hosted URL (judges watch the video or run it locally)
B. Public repo and local setup as the default, plus one hosted demo URL set up near the end if time allows
C. Keep the deployed public URL as approved, with the public repo alongside
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q9. [Way of Working] Follow-up: which model runs the submitted demo

The hackathon requires the Meta Model API (constraint C-T1). You'll develop with Claude and keep the model provider swappable (Q7). What must run on a Meta model by submission?

A. The submitted demo and the benchmark run on a Meta model; Claude is used only while building and for drafting the knowledge content
B. The demo runs on a Meta model; the benchmark may report Claude too, as a comparison
C. Whatever model is available at submission, Meta preferred
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q10. [Way of Working] Follow-up: the free model to start with

You asked for something free to begin with while Meta access is pending (Q7). Which should the swappable model setup include first?

A. Meta's open Llama models through a free hosted tier (e.g. Groq or OpenRouter free models): close to the Meta API, no cost
B. Llama running on your own machine through Ollama: free and offline, but slower and needs a download
C. Claude only until Meta credentials arrive (paid per use)
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Consolidated Summary Confirmation

- Way of working: a git repo, public on GitHub, committing straight to `main` with no branches (Q1, Q5)
- No thin slice first: features are built one after another; the approved Oct 31 deployed-slice milestone no longer holds and the dates get re-planned later (Q2, Q7)
- Testing: test-after, with each layer's tests written and run before its commit; 80% line coverage measured separately for backend and frontend, checked automatically on every push to `main`; plus a browser smoke test of the demo walk against the app running locally (Q3, Q4, Q8)
- Delivery: runs locally only; the public repo carries clear local setup instructions, and the submission is the repo plus the demo video, with no hosted URL (Q5, Q8)
- Code style, chosen for you: Ruff for Python; ESLint, Prettier and TypeScript strict mode for the frontend, checked automatically (Q6)
- Models: the model provider is swappable by configuration (Meta, Claude, others); you develop with Claude, and the first free option is Meta's open Llama models on a free hosted tier (Q7, Q10)
- Knowledge content: drafted with Claude while building, but the app itself can also generate it through the Meta or other configured models (Q7)
- Hard rule: the submitted demo and the benchmark run on a Meta model; Claude is only for building and drafting content (Q9)
- Hard rules carried from the hackathon and your workspace: synthetic data only; "decision support, not diagnosis" on every screen; grounded, cited answers only; secrets in environment variables and never in the public repo; no plaintext `data/*.json` committed; submission before Nov 4, 2026, 9:00 PM ET

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
