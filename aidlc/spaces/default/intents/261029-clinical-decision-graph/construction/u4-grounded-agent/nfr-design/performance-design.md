# Performance Design — u4-grounded-agent

Upstream: `performance-requirements.md`, `tech-stack-decisions.md`, `functional-spec.md` (U4), and `contract-summary.md` (C8).

- **NFR1.1:** The walk route is an async generator. It yields `progress: reading_findings` before it calls the gateway. The gateway is synchronous, so its calls run in `anyio.to_thread`.
- **NFR1.2 and NFR1.4:** The walk makes one `write_section` call per section, in order. It yields a section's lines as soon as they are checked. Sections with no walked nodes are skipped.
- **NFR1.3:** The guard's vocabulary (drug, test and diagnosis names and synonyms, and unit patterns) is built once for each pack version and cached.
