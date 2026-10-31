# Security Requirements — u4-grounded-agent

Upstream: `functional-spec.md` and `rules.md` (U4), `requirements.md` (NFR2, NFR5–NFR8, FR15), `contract-summary.md` (C8).

- **NFR2.1 Groundedness:** no line or "why" sentence reaches the client unless it passes `check_line` (BR1). The demo case has 0 ungrounded lines (C-Q1).
- **NFR5.1 Secrets:** `BRAHMA_SESSION_SECRET` is read from the environment and listed in `.env.example` with an empty value. Model keys stay inside U2. The server refuses to start without a session secret, except under `BRAHMA_MODEL_PROVIDER=recorded`, where it uses a random per-process secret.
- **NFR6.1 Synthetic only:** the server has no import route. Doctor text is stored only within the case.
- **NFR7.1 Audit:** every finished walk writes a SessionRecord, and every rejected line writes `line_rejected` (BR1.4, BR4.5).
- **NFR7.2 Session and role:** the signed session cookie is HttpOnly with SameSite=Lax. The profile header for mounted routers is always set by the server (BR4.2).
- **NFR8.1 Input:** every request body is a Pydantic model. Chat text is capped at 4,000 characters. The server binds to 127.0.0.1 by default.
- **NFR8.2 Prompt injection:** doctor text and node content go to the model as delimited data. Model output is used only after it passes schema and guard checks, so it never chooses nodes (BR2.2).
- **FR15.1 Disclaimer:** every `done` event and node detail carries the disclaimer and the pack version.

## Threats Considered

- The model making up a dose: blocked by the guard.
- Prompt injection through chat: the model never chooses nodes.
- Session forgery: the session cookie is signed.
- A malicious page on localhost calling the API: requests require the session cookie and use SameSite cookies.
