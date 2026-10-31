# Security Requirements — u2-platform

Upstream: `functional-spec.md` and `rules.md` (U2 functional design), `requirements.md` (NFR5, NFR6, NFR7, NFR8, NFR11; C-R1, C-R3), `contract-summary.md` (C2, C3, C4).

U2 holds the clinical audit, the demo identities and every outbound call to a model provider. Its risks are leaked keys, a changed audit record, and patient data reaching a provider log.

| ID | Requirement | Target / check | Source |
|---|---|---|---|
| NFR5.1 | Provider keys come only from environment variables. They never appear in code, config files, logs, error messages, the audit or ModelCallLog | Test: a ConfigError names the variable, not the value; a grep test of the log output after a call with a fake key finds no key | NFR5 |
| NFR5.2 | `.env.example` lists every variable U2 reads with empty values; `.env` is git-ignored | File check in CI | NFR5, FR16.2 |
| NFR7.1 | Audit tables reject UPDATE and DELETE at the database level, and every write is one transaction | Tests attempt both and expect refusal; a mid-write failure test leaves the previous rows intact | NFR7, BR1.1 |
| NFR7.2 | Each audit and session row names its profile, pack version, provider and model where they apply | Validation tests (BR1.2) | NFR7 |
| NFR6.1 | Prompt and response text are never logged; ModelCallLog keeps only metadata | Log test after a call | NFR6, BR3.3 |
| NFR6.2 | Exports and audit hold synthetic data only. The export PDF says "Synthetic patient" and "Decision support, not diagnosis" | Export test checks both strings | C-R1, C-R2 |
| NFR8.1 | Every provider call has a timeout (default 45 s) and at most 2 retries; failures raise typed errors that the caller can show, and are never swallowed | Tests with a fake provider for timeout, 429, 500 and 401 | NFR8, FR14.4 |
| NFR8.2 | Structured output from a model is validated against its schema before use | Test with an invalid JSON response | NFR8, BR3.4 |
| NFR8.3 | Provider calls use HTTPS only; a non-https base URL is refused at start | Config test | NFR8 |
| NFR7.3 | Roles are checked on reviewer and system actions; the demo has no passwords, and no other access control is claimed | require_role tests; README states "demo profiles, no authentication" | FR11.1, C-R3 |

## Threats Considered

| Threat | Handling |
|---|---|
| A key committed to the public repo | Environment-only keys, `.env` ignored, no key in logs (NFR5.1, NFR5.2) |
| Changing what the audit says was shown | Database triggers plus no update path (NFR7.1) |
| Patient text in provider-side logs | Synthetic data only (C-R1); prompt text is never logged locally (NFR6.1) |
| A model returning malformed or injected output | Schema validation (NFR8.2); the U4 claim check stops ungrounded text |
| A hung provider blocking the walk | Timeout plus bounded retries (NFR8.1) |
