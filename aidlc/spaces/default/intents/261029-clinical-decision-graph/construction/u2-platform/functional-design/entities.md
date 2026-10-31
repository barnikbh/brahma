# Entities — u2-platform

Upstream: `unit-of-work.md` (U2: Audit, Identity, ModelGateway), `components.md`, `contract-summary.md` (C2 Audit, C3 Identity, C4 ModelGateway), `requirements.md` (FR9, FR11, FR14, NFR5, NFR7, NFR11), `stories.md` (US1.1, US1.2, US3.4, US7.1, US7.2).

```yaml
entities:
  - name: AuditEntry
    description: One append-only event record.
    attributes:
      - { name: entryId, type: identifier, required: true, unique: true }
      - { name: kind, type: enum, required: true, allowed: [case_created, patient_updated, session_recorded, explore, line_held_back, treatment_edit, prescription_signed, prescription_voided, acknowledgement, visit_recorded, proposal_created, proposal_published, proposal_rejected, disclaimer_accepted, benchmark_run, sign_in] }
      - { name: caseId, type: text, required: false }
      - { name: sessionId, type: text, required: false }
      - { name: profileId, type: text, required: true, constraints: "id only; U2 owns Profile" }
      - { name: packVersion, type: text, required: false, constraints: "e.g. IBD v1.3, stored as text" }
      - { name: provider, type: text, required: false }
      - { name: model, type: text, required: false }
      - { name: benchmarkRunId, type: text, required: false }
      - { name: payload, type: json, required: true, constraints: "at most 256 KB serialised" }
      - { name: createdAt, type: timestamp-utc, required: true }
    constraints:
      - "No update or delete, ever (enforced by the database)."

  - name: SessionRecord
    description: The snapshot of one walk as shown to the doctor.
    attributes:
      - { name: sessionId, type: identifier, required: true, unique: true }
      - { name: caseId, type: text, required: true }
      - { name: walkId, type: text, required: true, constraints: "plain identifier; U2 never imports U4" }
      - { name: profileId, type: text, required: true }
      - { name: packVersion, type: text, required: true }
      - { name: provider, type: text, required: true }
      - { name: model, type: text, required: true }
      - { name: inputs, type: json, required: true, constraints: "verbatim text plus confirmed findings" }
      - { name: pathNodeIds, type: list-of-text, required: true }
      - { name: answer, type: json, required: true, constraints: "sections and lines as shown, with node IDs and counts" }
      - { name: sources, type: list-of-text, required: true }
      - { name: explanation, type: json, required: true, constraints: "the why sentences with node chips" }
      - { name: outcome, type: enum, allowed: [answered, needs_data, out_of_knowledge, error], required: true }
      - { name: benchmarkRunId, type: text, required: false }
      - { name: createdAt, type: timestamp-utc, required: true }
    constraints:
      - "No update or delete, ever."

  - name: Profile
    description: A seeded demo identity.
    attributes:
      - { name: profileId, type: identifier, required: true, unique: true, constraints: "p-maya, p-urologist, p-reviewer, p-benchmark" }
      - { name: displayName, type: text, required: true }
      - { name: role, type: enum, allowed: [doctor, reviewer, system], required: true }
      - { name: specialty, type: text, required: false }
      - { name: demoRegistration, type: text, required: false, constraints: "labelled demo, e.g. DEMO-REG-0001" }
      - { name: listed, type: boolean, required: true, constraints: "false for the system profile" }

  - name: DisclaimerAcceptance
    description: A profile's acceptance of a disclaimer version for a pack version.
    attributes:
      - { name: acceptanceId, type: identifier, required: true }
      - { name: profileId, type: reference, references: Profile, required: true }
      - { name: disclaimerVersion, type: text, required: true }
      - { name: packVersion, type: text, required: true }
      - { name: acceptedAt, type: timestamp-utc, required: true }

  - name: ProviderConfig
    description: The active model provider, read from the environment at start (not stored).
    attributes:
      - { name: provider, type: enum, allowed: [meta, claude, llama_hosted, recorded], required: true }
      - { name: model, type: text, required: true }
      - { name: apiKeyEnv, type: text, required: true, constraints: "name of the environment variable holding the key; never the key itself" }
      - { name: baseUrl, type: url, required: false }
      - { name: requestsPerMinute, type: integer, required: true, min: 1, max: 1000 }
      - { name: timeoutSeconds, type: integer, required: true, min: 5, max: 120, default: 45 }

  - name: ModelCallLog
    description: One model call (append-only, but not part of the clinical audit).
    attributes:
      - { name: callId, type: identifier, required: true }
      - { name: provider, type: text, required: true }
      - { name: model, type: text, required: true }
      - { name: purpose, type: enum, allowed: [extract, narrate, explain, draft, plain_benchmark, followup], required: true }
      - { name: latencyMs, type: integer, required: true, min: 0 }
      - { name: inputTokens, type: integer, required: false }
      - { name: outputTokens, type: integer, required: false }
      - { name: attempts, type: integer, required: true, min: 1, max: 3 }
      - { name: error, type: text, required: false }
      - { name: createdAt, type: timestamp-utc, required: true }
```

## Summary

There are six entities. **AuditEntry** and **SessionRecord** form the append-only clinical record. **Profile** and **DisclaimerAcceptance** cover who is acting and what they accepted. **ProviderConfig** is configuration read from the environment. **ModelCallLog** records every model call for diagnosis (NFR11). Other units' identifiers (caseId, walkId, pack version) are stored as plain text, so U2 depends on no other unit.
