# Scalability Design — u4-grounded-agent

Upstream: `scalability-requirements.md` and `functional-spec.md` (U4).

- **NFR4.1:** uvicorn runs as a single process and a single worker. All services are created once in `create_app()` and shared across requests.
- **NFR4.2:** The walk and edit routes need the U3 tab lock. SQLite runs in WAL mode with a busy timeout, which U2 sets.
- **NFR4.3:** `run_walk` is synchronous. U7 runs walks one after another, and the ModelGateway token bucket throttles them.
