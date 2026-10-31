# Security Design — u5-knowledge-updates

Upstream: `security-requirements.md` and `tech-stack-decisions.md` (U5), `functional-spec.md` (U5), `contract-summary.md` (C9, X2).

- **SafeFetcher (NFR8.1)**
  - Parses the URL and allows only http and https.
  - Resolves the host with `socket.getaddrinfo` and refuses the request if any address is private, loopback, link-local, multicast, reserved or unspecified (`ipaddress` checks).
  - Follows redirects by hand, at most 3, and re-checks each hop.
  - Streams the body with `httpx`, using a total timeout of 20 s, and aborts once the body passes 10 MB.
  - Injects the resolver and the client, so tests run without network access.
- **Drafter (NFR8.2)**
  - The prompt wraps the source text in `<source_data>` and says it is data, never instructions.
  - The `DraftedChanges` schema has `extra="forbid"`. A drafted node ID that is not in the base version is rejected.
  - Every draft goes through U1's validator, via a dry-run `_apply_changes` and validate, before it is stored.
- **CopyChecker (NFR8.3)**
  - Normalises the source and the draft into word lists.
  - Flags a node if the draft contains any 26-word window from the source, using a set of source 26-gram hashes.
- **Audit (NFR7.1)**
  - Publish writes `proposal_published` after `create_version` succeeds.
  - Reject writes `proposal_rejected` in the same transaction as the status change.
- **Role (NFR7.2)**
  - The router takes the profile from the `X-Brahma-Profile` session header, which U4's server sets from the signed-in session, and calls C3 `require_role(profile, "reviewer")`.
- **Errors (NFR8.4)**
  - Typed errors are mapped to HTTP codes in a single exception handler on the router.
  - The scheduler logs each failure with the source ID and the error class only.
- **NFR5.1**: there are no secrets in this unit.
