# Entities — u5-knowledge-updates

Upstream: `unit-of-work.md` (U5), `contract-summary.md` (C1 create_version, C9, X2), `components.md` (KnowledgeUpdates).

The code lives in the module `brahma.updates`. Its tables use the `up_` prefix in the shared SQLite file.

| Entity | Key fields | Notes |
|---|---|---|
| Proposal | proposalId, pack, baseVersion, targetVersion (vX.Y+1 draft), proposerProfileId, origin (`doctor`, `drafted` or `scheduled`), changeSet (C1 ChangeSet JSON), comment, status (`proposed`, `published` or `rejected`), reviewerProfileId?, reviewComment?, publishedVersion?, createdAt, decidedAt? | Never live until it is published. |
| ProposalChange | proposalId, nodeId, before (JSON or null), after (JSON), sourcePassage?, copyFlag (bool) | One row per changed node, used for the before-and-after view. |
| LinkedSource | sourceId, pack, url, title, contentHash?, lastCheckedAt?, lastStatus | Added when a proposal links a URL. The scheduler re-checks it. |
| SourceCheckRun | runId, startedAt, finishedAt, checked, changed, failed, errors (JSON) | One row per scheduler run. |
| FetchedSource (value) | url, text, contentHash, bytes | Not stored. The text is data, never instructions. |

## Summary

There are four stored entities and one value object. Each Proposal owns its ProposalChanges. Publishing a Proposal calls C1 `create_version`.
