# Performance Requirements — u4-grounded-agent

Upstream: `functional-spec.md` and `rules.md` (U4), `requirements.md` (NFR1), `contract-summary.md` (C8).

- **NFR1.1** The first `progress` event is sent within 3 s of the walk POST, before any model call (BR4.4).
- **NFR1.2** The full demo pathway arrives within 60 s, measured on the submission model. The free Llama tier is logged for information only and has no pass/fail target.
- **NFR1.3** On the recorded provider, the guard plus traversal adds less than 500 ms per walk. A local timing test covers this.
- **NFR1.4** Model calls run one section at a time, so lines stream as each section passes the guard.
