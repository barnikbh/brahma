# Tech Stack Decisions — u5-knowledge-updates

Upstream: `functional-spec.md` (U5), `requirements.md` (NFR9, NFR12), `contract-summary.md` (C7, C9).

- **HTTP router:** FastAPI `APIRouter`. This unit adds `fastapi` as the first web dependency, and U4's server will use the same framework. The tests use FastAPI's `TestClient`, which needs `httpx`; httpx is already installed.
  - Alternatives considered:
    - Starlette alone: less validation.
    - Flask: synchronous, and has no Pydantic integration.
- **Fetching:** `httpx`, already a dependency, with streaming reads so the size cap can be enforced. HTML is reduced to text with the standard library `html.parser`; no new dependency is added for this.
- **Storage:** SQLite tables with the `up_` prefix in the shared file.
- **Quality:** pytest with an 80% floor on `brahma.updates`, `mypy --strict` and Ruff. HTTP calls are faked with respx, and the model with the recorded provider (NFR9, NFR12).
- **Performance:** publishing completes in under 2 s for the IBD pack. Drafting is bounded by the C4 timeout.
