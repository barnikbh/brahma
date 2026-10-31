# Scalability Requirements — u4-grounded-agent

Upstream: `functional-spec.md` (U4), `requirements.md` (NFR4, NFR10), team practices (local only).

- **NFR4.1** The app runs as one local process for one doctor, with a few tabs open at a time. No horizontal scaling is needed.
- **NFR4.2** Walks run one at a time per case, enforced by the tab lock. Different cases may walk at the same time; SQLite WAL handles this.
- **NFR4.3** The benchmark (U7) calls `run_walk` sequentially, within the U2 rate limit.
