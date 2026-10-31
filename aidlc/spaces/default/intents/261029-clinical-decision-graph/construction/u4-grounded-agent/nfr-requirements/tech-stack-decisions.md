# Tech Stack Decisions — u4-grounded-agent

Upstream: `functional-spec.md` (U4), `requirements.md` (NFR9, NFR10, NFR12), `contract-summary.md` (C7, C8), and U5's tech-stack decision (FastAPI).

- **Server:** FastAPI, already a dependency, with `uvicorn` added to run it. SSE is sent as a `StreamingResponse` of `text/event-stream`, so no SSE library is needed.
  - Alternative considered: Starlette alone, rejected because U5 already uses FastAPI.
  - Alternative considered: WebSockets, rejected because they are bidirectional and the walk stream only goes one way.
- **Sessions:** a cookie signed with `itsdangerous`, which comes with Starlette's `SessionMiddleware`. No new dependency beyond `uvicorn`.
- **Run command:** `python -m brahma.server`, which starts uvicorn on 127.0.0.1:8000.
- **Quality:** pytest with an 80% floor on `brahma.agent` and `brahma.server`, plus `mypy --strict` and Ruff. Tests use the recorded provider with fixtures for `extract`, `write_section` and `why`.
