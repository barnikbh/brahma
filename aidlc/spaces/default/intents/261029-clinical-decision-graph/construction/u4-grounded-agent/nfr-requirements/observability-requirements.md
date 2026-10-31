# Observability Requirements — u4-grounded-agent

Upstream: `functional-spec.md` and `rules.md` (U4), `requirements.md` (NFR11).

- **NFR11.1** Each walk writes JSON lines to `BRAHMA_LOG_PATH`, which defaults to `data/brahma.log`. Each line holds the walkId, caseId, node path, section timings, model-call metadata (from U2), the ungrounded count, and the error class and provider.
- **NFR11.2** No patient values, doctor text or keys are written to the log.
- **NFR11.3** `GET /api/health` returns the live pack versions and the provider name.
