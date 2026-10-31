# Monitoring Design — u4-grounded-agent

Upstream: `observability-design.md` and `reliability-design.md` (U4), and `functional-spec.md` (U4).

- **Health:** `GET /api/health` reports the live pack versions, the provider and the database status.
- **Health metric:** the share of successful walks. The `done` versus `error` count can be worked out from `data/brahma.log` and the U2 `pf_model_call_log` table.
- **Error-rate metric:** the error events per walk and the ungrounded count per walk, both in the log.
- **Alerting:** none, because this is a local demo. The demo checklist covers checking the log after each rehearsal.
