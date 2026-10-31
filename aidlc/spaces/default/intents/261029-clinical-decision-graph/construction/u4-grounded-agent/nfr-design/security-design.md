# Security Design — u4-grounded-agent

Upstream: `security-requirements.md`, `tech-stack-decisions.md`, `functional-spec.md` (U4), and `contract-summary.md` (C7, C8).

- **NFR2.1 (`Guard`):** `Guard.check_line` combines two sets of claims: the claims the model declared, and the claims the `ClaimScanner` finds in the text. `ClaimScanner` uses a regex for a number followed by a unit, plus a vocabulary match on names. The walk engine can emit a line only through `Guard`.
- **NFR5.1 (`ServerConfig.from_env`):** reads `BRAHMA_SESSION_SECRET`. When the provider is `recorded` and no secret is set, it uses a random secret.
- **NFR7.2 (sessions):** `SessionMiddleware` uses an HttpOnly, SameSite=Lax cookie. A `current_profile` dependency reads the session and returns 401 if it is missing. Mounted routers get the session's `X-Brahma-Profile` value through a dependency override, so a value sent by the client is never used.
- **NFR8.1 (input):** every body is a Pydantic model with `extra="forbid"`. Text is limited to 4,000 characters. uvicorn binds to `127.0.0.1`.
- **NFR8.2 (prompts):** doctor text and node content are placed inside `<case_data>` and `<node_data>` blocks. Model output goes through schema validation and then the guard. It never selects nodes.
- **NFR7.1 (audit):** `line_rejected` and SessionRecord are written through C2.
- **FR15.1:** `done` events and node details carry the disclaimer text and the pack version.
