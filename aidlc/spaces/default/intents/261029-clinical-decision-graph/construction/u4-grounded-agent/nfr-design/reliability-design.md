# Reliability Design — u4-grounded-agent

Upstream: `reliability-requirements.md` and `functional-spec.md` (U4), and `contract-summary.md` (C8 failure mid-stream).

- **NFR8.2:** The walk generator catches `ModelError` and `AgentError`. It yields an `error` event with the `retryable` flag from U2 and a plain message. Then it saves the walk as `error`.
- **NFR8.3:** `WalkRepository.save_progress` runs after every `section_done`, inside a transaction. When `continue` is called with a walkId, the walk restarts at `lastSectionDone + 1`.
- **NFR8.4:** The case view includes the latest walk's state.
- **NFR8.5:** Any exception inside `Guard` counts as a failed check. The walk then ends with `error` code `guard_failure`.
