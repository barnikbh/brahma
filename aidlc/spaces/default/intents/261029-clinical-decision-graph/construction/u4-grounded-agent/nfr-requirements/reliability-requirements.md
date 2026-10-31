# Reliability Requirements — u4-grounded-agent

Upstream: `functional-spec.md` and `rules.md` (U4), `requirements.md` (NFR8, FR5.9), `contract-summary.md` (C8 failure mid-stream).

- **NFR8.2 Errors surfaced:** if a gateway or guard error happens mid-stream, the server sends an `error` event with a plain message and a `retryable` flag. Lines already sent stay on screen (BR3.1).
- **NFR8.3 Resume:** a walk is saved after every completed section. Retry resumes after the last completed section and keeps every input (BR3.2).
- **NFR8.4 Dropped connection:** the case view returns the walk state, so the client can offer Retry.
- **NFR8.5 Fail closed:** if the guard itself raises an exception, the line is treated as failed and the walk ends with `error`. An unchecked line is never sent.
