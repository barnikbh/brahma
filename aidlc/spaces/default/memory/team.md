# Team-Level Rules

> This team's affirmed practices and corrections. Loaded after `org.md` as
> strict-additive guidance; contradictions with broader policy are rejected.
> Populated by the practices-discovery affirmation gate. Edit at the gate,
> not directly.

## Way of Working

- We keep the code in a git repository hosted publicly on GitHub, with `main` as the only branch. (Q1, Q5, Q8)
- We commit straight to `main`. There are no feature branches, no pull requests and no squash merges. (Q1)
- This replaces the `org.md` default for Construction work: Bolts do not get their own worktree branches that are squash-merged into `main`. Each Bolt's work lands as ordinary commits on `main`. (Q1)
- The model provider can be swapped by configuration, with no code change needed to move between Meta (Meta Model API), Claude, and a free hosted tier of Meta's open Llama models (for example Groq or OpenRouter free models). The free hosted Llama option is set up first, while Meta Model API credentials are pending. (Q7, Q10)
- We develop and test with Claude while Meta credentials are not available. (Q7)
- The knowledge content (the IBD graph) is drafted with Claude while building. The application also has its own way to generate knowledge content through the Meta model or any other configured model. (Q7)
- Which model runs the submitted demo and the benchmark is a hard rule; see `discovered-rules.md`. (Q9)

## Walking Skeleton

- We do not build a thin end-to-end slice first. For this project the walking-skeleton stance is off (`skeleton: off`): no first slice and no slice checkpoint. We build the features one after another. (Q2)
- The approved Oct 31 "thin slice deployed" milestone no longer holds. Delivery planning re-plans the dates. (Q2, Q7)
- We accept that the first slice was where a Meta API access problem would have shown up early. The swappable provider setup (Q7, Q10) lets work go ahead without Meta credentials. The risk that Meta access arrives late moves to delivery planning.

## Testing Posture

- **Methodology**: test-after
- **Methodology evidence**: The builder chose test-after (Q3, option A): build each layer, then write and run its tests. This matches the `org.md` default for a project with no affirmed posture. It keeps evening sessions moving while still producing tests in every piece of work.
- **Ordering**: implement each layer, then write and run that layer's tests before committing it to main.
- Coverage: 80% line coverage, measured separately for the Python backend and the TypeScript/React frontend. This is the `mvp` scope floor and is not lowered. (Q4)
- The checks run automatically in CI (GitHub Actions on the public repo) on every push to `main`: lint, tests, and both coverage floors. (Q4, Q6, Q8)
- End-to-end: a browser smoke test walks the demo case (sign-in, question, cited answer with the disclaimer, audit record) against the app running locally. There is no hosted URL to test against. (Q4, Q8)
- Tooling: pytest with pytest-cov for the backend and agent; Vitest with React Testing Library for the frontend; Playwright for the browser smoke test.
- Model calls are stubbed with recorded responses in unit tests and CI, so the public repo's CI needs no API keys and no network calls to a model provider.
- The ~20-case synthetic benchmark (pass = at least 95% of recommendations trace to a node and source) is a product deliverable run on demand against the real model, not part of the CI suite.
- The active Test Strategy (`Standard`) still sets test volume and types. Nothing here reduces it.

## Guard Policy

<!-- Affirmed by the team. Mode: strict, relaxed, or off. Strict here holds for every intent, whatever one person asks in chat; relaxed or off here applies to every intent whose policy came from its scope, unless project.md or the person sets another; changing this line changes it. A section under the retired Change Control heading, written by an earlier release, is still read. -->

## Deployment

- The application runs locally only. There is no hosted URL and no hosting provider. (Q5, Q8)
- The public GitHub repository carries clear local setup instructions: a README covering prerequisites, install, configuration and run steps, and an `.env.example` listing every required environment variable with no real values. (Q5, Q8)
- The submission is the public repository plus the demo video. Judges watch the video or run the app locally. (Q8)
- There is no staging or production environment, so the `org.md` deploy-on-merge to staging and the manual production approval gate do not apply to this project.
- A "release" is a commit on `main` that passes CI and the local browser smoke test. Rollback means reverting the commit on `main`.
- The commit the demo video is recorded from is tagged, so judges can run exactly what they watched. No commits after the submission deadline (Nov 4, 2026, 9:00 PM ET).

## Code Style

- Python: Ruff for both linting and formatting, configured in `pyproject.toml`; snake_case naming. (Q6)
- Frontend: ESLint and Prettier, with TypeScript `strict` mode; camelCase for values, PascalCase for components. (Q6)
- Lint and format checks run in CI on every push to `main`, and a failure fails the build. No pre-commit hook. (Q6)
- The builder asked us to choose these tools (Q6, option A). Agents read the linter configuration before making any style suggestion.
## Forbidden

<!-- Team-specific forbidden patterns -->

## Mandated

<!-- Team-specific mandates -->

## Corrections

<!-- Self-learning loop appends here. -->
