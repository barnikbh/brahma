# Contract Design — Questions

Context: `unit-of-work.md` and `unit-of-work-dependency.md` define eight units in one local backend process plus the React web app; `components.md` gives entity shapes; ADR-005 sets in-process calls and HTTP to the web app. Per your project rule to keep process detail light and pick sensible defaults instead of asking (`project.md`, Corrections), each answer below is a default from those sources. The summary at the end is your one check.

## Q1. [Contracts] Public or external API

A. None exposed: the app runs locally; the only HTTP API is between the local backend and the web app. External services (model providers, source URLs) are consumed, not exposed
B. Publish a public API for other tools
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: team-practices.md, Deployment: local only)

## Q2. [Contracts] Mechanism per boundary

A. Backend unit to backend unit: typed Python interfaces (Protocol classes with Pydantic models); backend to web app: REST over HTTP with JSON, and the walk as a Server-Sent Events stream of checked lines
B. Everything over HTTP, including between backend units
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: ADR-005; Pydantic gives the same schema for the in-process call and the HTTP API; Server-Sent Events is the simplest one-way stream for a browser)

## Q3. [Contracts] Ownership and breaking changes

A. The provider unit owns each contract; one repo and one builder, so a breaking change is made in the same commit as every consumer's update, with the contract test updated first; additive fields are safe because consumers ignore unknown fields
B. Versioned contracts with deprecation windows
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: one builder committing to `main`, team-practices.md)

## Q4. [Contracts] Errors, timeouts and retries

A. Typed error results in-process; HTTP errors as one JSON shape (`code`, `message`, `retryable`); the model gateway alone retries (at most twice, FR14.4); the web app shows Retry with inputs kept (FR5.9)
B. Each unit retries on its own
C. Not yet defined
X. Other (please specify)

[Answer]: A (default: requirements.md FR14.4, FR5.9, NFR8)

## Consolidated Summary Confirmation

- No public API: the only HTTP API is between the local backend and the web app; model providers and source URLs are consumed, not exposed (Q1)
- Backend units talk through typed Python interfaces with shared Pydantic models; the web app uses REST with JSON, and the walk streams as Server-Sent Events of checked lines (Q2)
- The provider unit owns each contract; a breaking change lands in the same commit as its consumers, contract test first; consumers ignore unknown fields (Q3)
- One error shape over HTTP (`code`, `message`, `retryable`); only the model gateway retries, at most twice; the web app shows Retry with inputs kept (Q4)

Does this all look correct before I generate the artifact?

- Looks correct
- Request changes

[Answer]: Looks correct
