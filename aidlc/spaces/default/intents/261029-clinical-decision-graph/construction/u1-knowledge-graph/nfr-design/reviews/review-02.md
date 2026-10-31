## Review

**Verdict:** READY
**Reviewer:** aidlc-architecture-reviewer-agent
**Date:** 2026-10-29
**Iteration:** 2
**Verdict Dictated:** no

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/nfr-design/security-design.md > NFR2.2 Exact claim matching | The design says numbers are compared with `==` "after conversion and rounding to the node's stated precision". No node field called precision exists in the functional design's FieldSchema (the drug `rounding` field is U3's dose rounding, not a match precision). Rounding the claim to a coarser precision lets 60.4 mg match a 60 mg node, which is the tolerance NFR2.2 and BR2.5 forbid. Conversion factors such as g/L to g/dL (divide by 10) also give wrong `==` results on binary floats. | Remove the rounding step. State that values and `UNIT_TABLE` factors are `decimal.Decimal` or `fractions.Fraction`, and that equality is exact after conversion. Add the named tests: 60 mg vs 60.4 mg fails, and a g/L to g/dL conversion matches exactly. | Resolved (reviewer) |
| R-02 | Major | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/nfr-design/security-design.md > NFR7.1 Immutable versions, NFR8.2 Atomic writes | Immutability triggers cover only `BEFORE UPDATE`. Nothing blocks `DELETE` on `kg_node`, `kg_edge`, `kg_source` or `kg_pack_version`, so a published version can still be gutted, and the status trigger does not stop `superseded` going back to `live`. "Exactly one live version per pack" (entities.md) has no enforcement, and the next-minor-number step reads then writes inside a deferred `with conn:`. Under WAL with FastAPI worker threads, two overlapping publishes can both succeed or fail with an immediate SQLITE_BUSY_SNAPSHOT that the busy timeout does not cover. | Add `BEFORE DELETE` triggers on the immutable tables and limit the status trigger to the `live` to `superseded` change. Add a partial unique index on `kg_pack_version(pack_id) WHERE status='live'`. Start create_version and load_pack with `BEGIN IMMEDIATE`. Add tests for delete refusal and for two concurrent publishes. | Resolved (reviewer) |
| R-03 | Major | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/nfr-design/traceability.json > upstream_ids; logical-components.md > NFRs it carries | The design covers only the security-requirements NFRs. The derived requirements in tech-stack-decisions.md have no design or test: NFR11.1 (one log line per pack load and version creation: pack, version, node count, duration, result), NFR10.1 (packs load in under 2 s), NFR9.1 (80% coverage on U1's package) and NFR12.2 (full typing). NFR1.1 is credited to `GraphIndex` but no test or measurement is named. NFR12.1 is also one coverage row for two different requirements (Ruff, and paraphrase). | Add rows for NFR1.1, NFR9.1, NFR10.1, NFR11.1 and NFR12.2 to the design and to traceability.json. For each, name the mechanism: a logging call in `KnowledgeService`, a timing test on a 2,000-node fixture, the pytest-cov floor and a type-check step. Give the two NFR12.1 meanings separate rows. | Resolved (reviewer) |
| R-04 | Major | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/nfr-design/logical-components.md > Shared Resources; security-design.md > NFR8.2 | WAL mode, the busy timeout and foreign keys are "set once by the shared database helper". No contract, unit or component defines that helper. U1 has `depends_on: []` and must build and test alone (U2 is also `depends_on: []`), so U1 cannot import it. NFR5.1 and the shared-file arrangement depend on it. | Make the helper a U1-local function (`kg_connect(path)`) that applies the pragmas, with a test that checks them. If U2 should own a common helper, record that in the shared contracts and the dependency graph instead. | Resolved (reviewer) |
| R-05 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/nfr-design/security-design.md > NFR6.1 | The design caps `content` at 2,000 characters, but entities.md sets no such limit, so the design and the data model disagree. `extra="forbid"` guards only the top level of the model: patient data can still sit in `content` or in the free `fields` map. The only guard for that is a manual checklist. | Either add the 2,000-character cap to entities.md or drop it from the design. Add a cheap load-time scan that rejects obvious dates, emails and long digit runs in `content` and string fields. Keep the checklist as a second layer. | Resolved (reviewer) |
| R-06 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/nfr-design/security-design.md > NFR8.1 Safe parsing | "`yaml.safe_load` with a custom loader" is contradictory, because `safe_load` takes no loader argument. Rejecting unsafe tags and rejecting aliases are separate behaviours, and the NFR8.1 tests named upstream cover only the unsafe tag and the oversize file. | Specify `yaml.load(text, Loader=NoAliasSafeLoader)`, where the loader subclasses `SafeLoader`. Add tests for an alias, an unsafe tag, an oversize file and a non-YAML extension. | Resolved (reviewer) |
| R-07 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/nfr-design/security-design.md > NFR6.2 and Input Validation Summary | A bad comment raises `ValueError`, but functional-spec.md lists only typed errors and BR2.7 refuses an unknown nodeId (a `NodeNotFound`). The design does not say whether the 1 to 1,000 length check runs before or after control characters are stripped, or what happens to blank text. | Name a typed comment error and use `NodeNotFound` for an unknown ID. State that the length check runs after stripping and that blank text is refused. | Resolved (reviewer) |
| R-08 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/nfr-design/logical-components.md > kg_connect(path) | BEGIN IMMEDIATE is relied on for NFR8.2, but the connection's transaction mode is not stated. Python's sqlite3 module opens implicit transactions by default, and an explicit BEGIN then errors or behaves unpredictably. | State that kg_connect opens the connection with isolation_level=None (autocommit) so that explicit BEGIN IMMEDIATE and COMMIT control the transaction. | New |
| R-09 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/nfr-design/logical-components.md > GraphIndex and NFR1.1 | The index is built once per version and then cached, but it is not stated when. The 50 ms test takes the median of 20 runs, so a slow first call after a publish would not be caught. | Say that the index is built at load or version creation, or add a cold-call build-time test for a 2,000-node pack. | New |
| R-10 | Minor | aidlc/spaces/default/intents/261029-clinical-decision-graph/construction/u1-knowledge-graph/nfr-design/security-design.md > NFR6.1 patient-data scan | The date pattern d{1,2}[/-]d{1,2}[/-]d{2,4} and the 8-or-more-digit rule could reject legitimate clinical text, such as a dosing schedule like "6-8-12 weeks". No allow-list or false-positive test is named. | Add a false-positive fixture test for common clinical patterns, or tighten the date pattern, for example by requiring a plausible month and day. | New |

> R-01 Reviewer note: ClaimMatcher now parses to Decimal from strings, holds an exact Decimal UNIT_TABLE and uses == with no rounding or tolerance. Named tests cover 60.4 vs 60 and 102 g/L vs 10.2 g/dL.

> R-02 Reviewer note: BEFORE UPDATE and BEFORE DELETE triggers cover all tables, superseded back to live is blocked, a partial unique index enforces one live version, and BEGIN IMMEDIATE is used. Tests are named for each.

> R-03 Reviewer note: NFR1.1, NFR9.1, NFR10.1, NFR11.1 and NFR12.2 now each have a design and a test or CI check. The two NFR12 meanings are separated and labelled.

> R-04 Reviewer note: The undefined shared helper is replaced by a U1-local kg_connect that sets WAL, busy_timeout and foreign_keys.

> R-05 Reviewer note: The unsupported cap is removed and stated as absent. A patient-data scan on content and fields is added with tests.

> R-06 Reviewer note: NoAliasSafeLoader is defined as a SafeLoader subclass that refuses aliases. Alias, tag, 6 MB and extension tests are named.

> R-07 Reviewer note: CommentInvalid and NodeNotFound are typed, strip happens before the length check, and blank text is refused.

### Validation Tool Results

| Tool | Result | Interpretation |
|---|---|---|
| None listed for this stage | Not run | I checked cross-references by hand against nfr-requirements/tech-stack-decisions.md and security-requirements.md. All upstream NFR IDs resolve. |

### Summary

All seven prior findings are fixed. The remaining items are Minor implementation-clarity points (autocommit mode, when the index is built, and false positives in the scan). A developer could build U1 from this design.
