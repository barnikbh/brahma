# Security Design — u1-knowledge-graph

Upstream: `security-requirements.md` and `tech-stack-decisions.md` (U1 NFR requirements), `functional-spec.md` and `rules.md` (U1), `contract-summary.md` (C1), `requirements.md`.

## Design

| Requirement | Design | Tests |
|---|---|---|
| NFR2.1 Sourced nodes only | `PackValidator` runs on every load and every `create_version`. It checks sources (BR1.1), edges and ID prefixes (BR1.2), required fields per type (BR1.4), placeholders (BR3.5) and the patient-data scan (NFR6.1). It raises `PackLoadError` with the first offending node or edge ID before anything is written. | Sourceless node, cross-pack ID, missing drug field and `[60 mg]` placeholder each fail with the node named |
| NFR2.2 Exact claim matching | `ClaimMatcher` is a pure function module. Text is normalised (lowercase, trim, collapse spaces) and synonyms resolved from the node's `synonyms`. Numbers are parsed into `decimal.Decimal` from their string form, and `UNIT_TABLE: dict[measure, dict[unit, Decimal]]` holds exact factors such as `{"Hb": {"g/dL": 1, "g/L": Decimal("0.1")}}`. Equality is `==` on the converted Decimals, with no rounding, tolerance, fuzzy matching or model call. | 60 mg vs node 60 mg passes; 60.4 mg vs 60 mg fails; Hb 102 g/L vs node 10.2 g/dL passes exactly; drug synonym passes; unit not in the table returns `unknown_unit` |
| NFR6.1 No patient data | Node and Edge models set `extra="forbid"`. On load, `PackValidator` scans `content` and every string inside `fields` for obvious personal data: dates (`\d{1,2}[/-]\d{1,2}[/-]\d{2,4}`, ISO dates), email addresses and runs of 8 or more digits. A match rejects the load. Before load you also tick a manual checklist item, "No real names, IDs or dates in content". There is no content-length cap; entities.md sets none. | Schema fixture test (no patient-like fields); a node containing an email address, and one containing `12/03/1990`, each fail the load |
| NFR8.1 Safe parsing | `yaml.load(text, Loader=NoAliasSafeLoader)`. `NoAliasSafeLoader` subclasses `yaml.SafeLoader`, so unsafe tags are refused, and overrides alias composition to raise, so anchors and aliases are refused. Before reading, the loader checks the file is at most 5 MB and has a `.yaml` or `.yml` extension. | Alias, `!!python/object` tag, 6 MB file and `.json` extension are each refused |
| NFR8.2 Atomic writes | Every write runs in one transaction. `load_pack` and `create_version` begin with `BEGIN IMMEDIATE`, which takes the write lock before reading the current live version and the next number, so two overlapping publishes cannot both succeed. The second waits up to the busy timeout and then fails with `PackBusy`. Connection settings come from `kg_connect` (logical-components.md). | Interrupted write leaves the previous version intact; two concurrent `create_version` calls give one success and one `PackBusy` or a later sequential success, and never two live versions |
| NFR7.1 Immutable versions | The repository exposes no update or delete for nodes, edges, sources or versions except `supersede(version_id)`. SQLite triggers back this up: `BEFORE UPDATE` and `BEFORE DELETE` on `kg_node`, `kg_edge` and `kg_source` abort; on `kg_pack_version`, `BEFORE DELETE` aborts, and `BEFORE UPDATE` aborts unless the only change is `status` from `live` to `superseded`. A partial unique index on `kg_pack_version(pack_id) WHERE status = 'live'` enforces exactly one live version per pack. | Update and delete attempts on each table are refused; `superseded` back to `live` is refused; a second live row is refused by the index |
| NFR5.1 No secrets | U1 reads one setting, `BRAHMA_DB_PATH` (default `./data/brahma.db`). The `data/` directory is git-ignored, per the workspace rule. | Config test |
| NFR6.2 Comment text | `add_comment` strips control characters except newline, then checks 1–1,000 characters; blank text after stripping is refused. Failures raise `CommentInvalid(reason)`, and an unknown nodeId raises `NodeNotFound`. Text is stored as given; U1 never renders HTML, and U8 escapes on display. | Markup round-trips unchanged; blank, 1,001-character and unknown-node comments are refused with the right error |
| NFR12.1 (paraphrase meaning, from security-requirements.md) | The authoring script `scripts/check_copy.py` compares each node's content with the source passages you keep outside the repo and flags runs of more than 25 words. It is run before load as a manual checklist step (BR3.6). | Script test with a 26-word copied run |

## Typed Errors (added to the functional spec's list)

| Error | Raised by |
|---|---|
| `PackLoadError(id, reason)` | Validation, including the patient-data scan |
| `PackBusy` | Write lock not obtained within the busy timeout |
| `CommentInvalid(reason)` | Blank or over-length comment |
| `NodeNotFound(nodeId)` | Unknown node for a read or a comment |

## Input Validation Summary

| Input | Validated by | On failure |
|---|---|---|
| Pack file | Size, extension, `NoAliasSafeLoader`, Pydantic models, PackValidator | PackLoadError; nothing written |
| ChangeSet (from U5) | Pydantic, then PackValidator on the resulting version | PackLoadError; nothing written |
| Facts and claims (from U4, U7) | Pydantic models; unknown units go to `unknownUnit` | Typed result, never an exception for bad data |
| Comment | Strip, then length and blank check | CommentInvalid or NodeNotFound |
