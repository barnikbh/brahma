# Security Requirements — u1-knowledge-graph

Upstream: `functional-spec.md` and `rules.md` (U1 functional design), `requirements.md` (NFR2, NFR5, NFR6, NFR8, NFR9, NFR12; C-R1, C-R4), `contract-summary.md` (C1). U1 is a library with no network access, no user input of its own and no secrets. Its risks are bad content getting in and stored data being changed.

| ID | Requirement | Target / check | Source |
|---|---|---|---|
| NFR2.1 | Every node a walk can reach carries at least one known source; a pack missing one cannot load | Load test with a sourceless node fails and names it (BR1.1) | NFR2, FR1.2 |
| NFR2.2 | `match_claims` is exact: numbers equal after unit conversion, text equal after normalisation and synonyms. No fuzzy or model-based matching | Unit tests with a 60 mg vs 120 mg mismatch, a unit not in the table, and a drug synonym | NFR2, FR4.10 |
| NFR6.1 | Packs contain clinical knowledge only. No patient data is stored in U1 | Schema has no patient fields; a review of the pack files finds no names or IDs | NFR6, C-R1 |
| NFR8.1 | Pack loading parses files with safe settings (no code execution, no custom tags), caps each file at 5 MB and rejects any other format | Loader test with an unsafe tag and an oversize file | NFR8 |
| NFR8.2 | All writes (load, create_version, add_comment) are single transactions; a failure leaves stored data unchanged | Test that kills a write mid-way and checks the previous version is intact | NFR8, BR1.3 |
| NFR7.1 | Published versions can't be changed: the storage layer has no update path for nodes, edges or versions except the status flag, and a test proves it | Test attempts an update and expects refusal | NFR7, BR1.3 |
| NFR5.1 | U1 needs no secrets or keys | No environment variables are read by U1 except the database path | NFR5 |
| NFR6.2 | Comment text is stored as plain text and escaped by the screens that show it (U8); U1 does no HTML rendering | Comment with markup round-trips unchanged | NFR6 |
| NFR12.1 | Guideline content is paraphrased (BR3.6) and every node cites a source, so U1 doesn't distribute copied text | Authoring check before load | C-R4, FR2.5 |

## Threats Considered

| Threat | Handling |
|---|---|
| A malformed or hostile pack file | Safe parser settings, size cap, strict validation (NFR8.1, BR1.x) |
| A drafted change sneaking in uncited content | `create_version` re-runs every load check (BR1.3) |
| A model-written line passing the check through loose matching | Exact matching only (NFR2.2) |
| Direct edits to the database file | Out of scope for a local single-user app; immutability is enforced at the storage layer, and the audit (U2) records publishes |
