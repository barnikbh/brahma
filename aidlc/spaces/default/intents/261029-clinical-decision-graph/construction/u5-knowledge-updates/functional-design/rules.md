# Business Rules — u5-knowledge-updates

Upstream: `requirements.md` (FR10.1–FR10.9), `stories.md` (US8.1–US8.3), `contract-summary.md` (C1, C9, X2).

## Proposals (BR1)

- **BR1.1** When a doctor submits a proposal, it has a node, a change, and a comment. It may also have a source URL and a section. It is stored as `proposed` against the pack's current live version, with target version vX.Y+1 draft (FR10.1, FR10.3).
- **BR1.2** Each proposal stores a ChangeSet together with per-node before and after values. Its change summary is the proposal comment.
- **BR1.3** Only a profile with the reviewer role may publish or reject a proposal (C3 `require_role`). Any other profile gets Forbidden, which the API returns as 403 (FR10.4).
- **BR1.4** A proposal that has any copy flag can't be published. The API returns 409 (FR10.9, AC8.2.3).
- **BR1.5** Publishing calls C1 `create_version(pack, base, changeSet, reviewer)`. If the base is no longer live, the change set is re-applied to the current live version. If the change set no longer validates, the proposal stays `proposed` and the error is returned. On success, the proposal is marked `published` with the new version, and `proposal_published` is written to the audit (FR10.5).
- **BR1.6** Rejecting a proposal stores the reviewer comment and writes `proposal_rejected` to the audit.
- **BR1.7** Version history merges C1 `list_versions` (Live and Superseded) with this unit's proposals (Proposed and Rejected). Each entry shows the version, status, date, author, change and comment (FR10.6).

## Sources (BR2, FR10.9)

- **BR2.1** A source URL is fetched only when all of these hold:
  - it uses http or https;
  - its host resolves only to public addresses (not loopback, private, link-local or reserved);
  - each redirect target passes the same check.
- **BR2.2** A fetch is capped at 10 MB and 20 s. HTML is reduced to plain text. Any failure raises SourceFetchError with a reason.
- **BR2.3** A drafted node text that repeats more than 25 consecutive words of the source sets copyFlag. Words are compared after lowercasing and stripping punctuation.
- **BR2.4** The source passage is the part of the source that best overlaps each changed node. For a doctor proposal, it is the section the doctor quoted.

## Drafting (BR3, FR10.2, Should)

- **BR3.1** Drafting sends one structured-output call to C4, with purpose `draft_proposal`. The source text goes inside a delimited data block, with an instruction to treat it as data only. The output must validate against the DraftedChanges schema, which allows updates to existing node IDs only.
- **BR3.2** Each drafted change goes through U1 validation and the copy check before the proposal is stored. If the model call fails, no proposal is stored and the error is returned.

## Scheduler (BR4, FR10.7, Could)

- **BR4.1** `check_sources()` re-fetches each linked source. When the content hash has changed, it drafts a proposal with origin `scheduled`. A failure is logged and recorded, and the run continues with the next source. Each run is recorded as a SourceCheckRun.
- **BR4.2** The run is triggered by `python -m brahma.updates.check` or by an interval in the server. The interval is set by `BRAHMA_SOURCE_CHECK_HOURS`, default 24, and 0 turns it off.

## Summary

There are 15 rules in four groups. No change becomes live without a reviewer publishing it.
