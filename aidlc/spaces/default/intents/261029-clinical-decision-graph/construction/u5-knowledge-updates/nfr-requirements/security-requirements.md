# Security Requirements — u5-knowledge-updates

Upstream: `functional-spec.md` and `rules.md` (U5), `requirements.md` (NFR5–NFR8, FR10.9), `contract-summary.md` (C9, X2).

- **NFR8.1 SSRF and limits:** fetches allow http and https only. Every resolved address, including redirects (at most 3), must be public. Each fetch is capped at 10 MB and 20 s. A refusal names its reason (BR2.1, BR2.2).
- **NFR8.2 Prompt injection:** source text reaches the model only as delimited data. The output must match a schema, and drafts may update existing node IDs only. U1 validates every change before it is stored. No proposal goes live without a reviewer (BR3, BR1.3).
- **NFR8.3 Copying:** a proposal that repeats more than 25 consecutive words of its source can't be published (BR2.3, BR1.4).
- **NFR7.1 Audit:** publishing and rejecting are written to the C2 audit with the reviewer and comment (BR1.5, BR1.6).
- **NFR7.2 Role check:** publish and reject require the reviewer role. The API checks the session profile, not a profile the client sends (BR1.3).
- **NFR5.1 Secrets:** model keys stay in U2. U5 reads no keys.
- **NFR8.4 Errors surfaced:** typed errors, mapped to HTTP codes, with plain messages. A scheduler failure is logged per source, and the run continues.

## Threats Considered

- SSRF to localhost or cloud metadata addresses: addressed by NFR8.1.
- A malicious page steering the drafter: addressed by NFR8.2.
- Verbatim copying of guideline text: addressed by NFR8.3.
- A doctor publishing without review: addressed by NFR7.2.
