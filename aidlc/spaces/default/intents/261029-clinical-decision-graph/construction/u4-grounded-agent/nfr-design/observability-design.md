# Observability Design — u4-grounded-agent

Upstream: `observability-requirements.md` and `functional-spec.md` (U4).

- **NFR11.1:** `WalkLogger` writes one JSON line per walk event (start, section, done or error) to `BRAHMA_LOG_PATH`, which defaults to `data/brahma.log`. Each line holds the walkId, caseId, node IDs, timings, counts, error class and provider. Model-call metadata comes from U2's call log.
- **NFR11.2:** The logger uses an allow-list of fields. Text fields are never logged, and a test checks this.
- **NFR11.3:** `GET /api/health` returns the live pack versions and the provider.
