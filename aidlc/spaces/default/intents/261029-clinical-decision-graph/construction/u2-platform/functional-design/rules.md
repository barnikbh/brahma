# Business Rules — u2-platform

Upstream: `requirements.md` (FR9.1–FR9.5, FR11.1–FR11.2, FR14.1–FR14.4, NFR5, NFR7, NFR11), `stories.md` (US1.1, US1.2, US3.4, US7.1, US7.2), `contract-summary.md` (C2, C3, C4), `entities.md`.

```yaml
rules:
  - id: BR1.1
    statement: Audit entries and session records are append-only.
    category: constraint
    applies_to: AuditEntry, SessionRecord
    trigger: any write
    logic: >
      The audit module exposes only append, record_session and read operations. The database rejects UPDATE
      and DELETE on audit tables with triggers. Every write is one transaction, so a crash leaves the last
      committed entry intact and no partial row.
    violation: an attempted update or delete raises AuditImmutable; nothing changes
    source: FR9.2, NFR7
  - id: BR1.2
    statement: Every entry names the acting profile, and the pack version, provider and model when they apply.
    category: validation
    applies_to: AuditEntry, SessionRecord
    trigger: append, record_session
    logic: >
      IF profileId is missing or unknown THEN refuse. Audit and Identity both read the profiles table through
      a small repository inside U2, so Audit doesn't import Identity. Session records also require packVersion,
      provider and model, all passed by the caller in SessionRecordIn (contract C2, updated). Payloads over
      256 KB are refused.
    violation: AuditInvalid(reason)
    source: FR9.1, FR14.3, NFR7
  - id: BR1.3
    statement: History lists sessions newest first, filtered by outcome and text, with benchmark sessions hidden unless asked for.
    category: policy
    applies_to: list_sessions
    trigger: list_sessions(filter)
    logic: >
      Text matches the inputs' verbatim text, finding names, the answer's sub-type label, or the session ID,
      case-insensitively. An outcome filter matches exactly. Sessions with a benchmarkRunId are excluded unless
      includeBenchmark is true or benchmarkRunId is given. No match returns an empty list (the screen says
      "No sessions yet" or "No sessions match").
    violation: n/a
    source: FR9.4
  - id: BR1.4
    statement: Export gives the full session record as JSON and as a readable PDF with the disclaimer and a synthetic-data label.
    category: policy
    applies_to: export_session
    trigger: export_session(sessionId, format)
    logic: JSON is the session record plus its audit entries. The PDF shows the inputs, path, answer, sources, why, profile, pack version, provider and timestamps, with "Decision support, not diagnosis" and "Synthetic patient" in the header. An unknown session raises SessionNotFound.
    violation: SessionNotFound; PDF generation failure raises ExportFailed and returns nothing partial
    source: FR9.5
  - id: BR2.1
    statement: Sign-in is picking a listed demo profile; there is no password.
    category: authorization
    applies_to: Profile
    trigger: list_profiles, get_profile
    logic: Three listed profiles (Dr. Maya gastroenterologist, demo urologist, demo clinical reviewer) and one unlisted system profile (Benchmark runner) are seeded at first start. Signing in as an unknown or unlisted profile is refused.
    violation: ProfileNotFound
    source: FR11.1
  - id: BR2.2
    statement: A profile must accept the current disclaimer for the current pack versions before using the app; acceptance is asked again when either changes materially.
    category: policy
    applies_to: DisclaimerAcceptance
    trigger: needs_disclaimer, accept_disclaimer
    logic: >
      The caller (the U4 server) passes the current disclaimerVersion (a constant in the app, e.g. "1") and
      the live pack versions string, formatted as "IBD 1.3; URO 0.1" with packs sorted by code. needs_disclaimer
      is true when the profile has no acceptance with that disclaimerVersion whose pack string has the same pack
      codes and the same major number for each pack. A pack change counts as material when its major number
      changes or a pack is added. Acceptance is stored once and also written to the audit as disclaimer_accepted.
    violation: n/a
    source: FR11.2
  - id: BR2.3
    statement: Reviewer-only and system-only actions check the role.
    category: authorization
    applies_to: require_role
    trigger: require_role(profileId, role)
    logic: IF the profile's role differs THEN raise Forbidden
    violation: Forbidden
    source: FR10.4
  - id: BR3.1
    statement: The model provider is chosen by configuration only.
    category: policy
    applies_to: ProviderConfig
    trigger: app start
    logic: >
      BRAHMA_MODEL_PROVIDER selects meta, claude, llama_hosted or recorded, and BRAHMA_MODEL_NAME the model.
      Keys come from environment variables (META_API_KEY, ANTHROPIC_API_KEY, LLAMA_API_KEY). A missing key for
      the chosen provider stops start-up with a clear message naming the variable, never the value. Optional:
      BRAHMA_MODEL_BASE_URL (provider default), BRAHMA_MODEL_RPM (default 30), BRAHMA_MODEL_TIMEOUT_S (default 45).
      The recorded provider replays saved responses for tests and CI. The U4 server writes a sign_in audit entry
      when a profile is picked.
    violation: ConfigError at start
    source: FR14.1, FR14.2, NFR5
  - id: BR3.2
    statement: Calls are throttled to the provider's rate and retried at most twice on retryable errors.
    category: policy
    applies_to: complete
    trigger: complete(request)
    logic: >
      A token bucket enforces requestsPerMinute. Timeouts, 429 and 5xx are retryable: wait 1 s then 3 s
      (with the provider's Retry-After when larger), up to 2 retries (3 attempts in all). 401 and 403 are not
      retried. After the last attempt, raise the typed error.
    violation: ModelTimeout, ModelRateLimited, ModelAuthError or ModelUnavailable, each with provider and retryable
    source: FR14.4, FR13.8
  - id: BR3.3
    statement: Every model call is logged, whether it succeeds or fails.
    category: policy
    applies_to: ModelCallLog
    trigger: complete
    logic: After each call (including failures), write one ModelCallLog row and one JSON log line with provider, model, purpose, latency, tokens, attempts and error. Prompt and response text are not logged.
    violation: n/a
    source: NFR11
  - id: BR3.4
    statement: Structured output is requested through a JSON schema when the provider supports it; otherwise the text is parsed and validated against the schema.
    category: calculation
    applies_to: complete
    trigger: request with responseSchema
    logic: IF the provider supports JSON-schema output THEN ask for it; ELSE extract the first JSON object from the text. Either way, validate it against the schema. A response that fails validation counts as one of the 2 retries; if it is the last attempt, ModelUnavailable is raised.
    violation: ModelUnavailable(reason="invalid structured output")
    source: FR14.1, contract C4 open question
```

## Summary

| ID | Category | Rule | Source |
|---|---|---|---|
| BR1.1 | constraint | Audit is append-only, enforced in the database | FR9.2, NFR7 |
| BR1.2 | validation | Entries name the profile, pack version, provider and model | FR9.1, FR14.3 |
| BR1.3 | policy | History filters; benchmark sessions hidden | FR9.4 |
| BR1.4 | policy | JSON and PDF export with the disclaimer | FR9.5 |
| BR2.1 | authorization | Pick a demo profile, no password | FR11.1 |
| BR2.2 | policy | Disclaimer accepted per version, re-asked on material change | FR11.2 |
| BR2.3 | authorization | Role checks | FR10.4 |
| BR3.1 | policy | Provider by configuration; keys from the environment | FR14.1, FR14.2, NFR5 |
| BR3.2 | policy | Throttle; at most 2 retries; typed errors | FR14.4 |
| BR3.3 | policy | Every call logged, without prompt text | NFR11 |
| BR3.4 | calculation | Structured output validated against a schema | FR14.1 |
