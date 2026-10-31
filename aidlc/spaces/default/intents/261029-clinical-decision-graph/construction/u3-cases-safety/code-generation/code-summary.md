# Code Summary — u3-cases-safety

## Built

The `brahma.cases` library is the C5 `CaseService`. It covers:

- Synthetic patients and cases: IDs of the form `BR-xxxxxx`, search that excludes benchmark cases, a version pin, and `newer_version`.
- The append-only chat thread, enforced by triggers. A form can go from open to submitted once. Drafts are kept until submit.
- Finding validation per FR4.11: unit conversion that keeps the entered value, plus the invalid, conflict and confirm-range states. A walk is gated by `findings_ready`.
- A one-tab lock that expires 45 s after the last heartbeat.
- Dose computation, absolute or per kg, with the formula shown.
- Allergy, pregnancy, interaction and duplicate-class safety checks. A check is never `ok` without a node; with no node it is "Not checked".
- Treatment edits, each followed by a re-run of the dose and safety checks.

Patient updates, case creation and edits write to the audit in the same transaction as the case change.

## Files

- **Created:**
  - `src/brahma/cases/`: errors, models, db, repository, catalog, findings, safety, service
  - `tests/cases/`: 5 test files, conftest, and the `fixtures/safety_pack.yaml` test pack
- **Modified:** `.github/workflows/ci.yml` (the U3 mypy and coverage steps)

## Tests (from the build run)

- `pytest tests/cases --cov=brahma.cases`: 47 passed, 99% coverage
- Full suite: 193 passed, 97.58% coverage
- Ruff, Ruff format and `mypy --strict`: clean

## Deviations

1. The audit kind is `treatment_edit`, matching U2's enum.
2. The same-transaction audit uses U2's `AuditRepository.add_entry` on the shared connection, because `AuditService.append` opens its own transaction.
3. Nodes by type are read through U1's repository via `catalog.py`. A public `nodes_by_type` method on U1 would be cleaner later.
4. `apply_edit` returns `{edit, dose, safety}`, as BR4.4 asks.
5. Before a pin, the live IBD version is used.

## Pack Gaps (for the content reviewer, by Oct 31)

The IBD pack lacks several things the checks need. Until these are added, the demo panel shows "Not checked" for most interaction checks:

- No metric plausible ranges, so confirm-range never triggers.
- No penicillin-class drug.
- No drug with a pregnancy contraindication.
- No dose rounding rules.
- Only one interaction node, levothyroxine with calcium or iron, so the IBD therapies show "Not checked" for interactions.

All of these paths are tested with the inline test pack.
