# Business Rules — u3-cases-safety

Upstream: `requirements.md` (FR1.6, FR1.7, FR4.9, FR4.11, FR6, FR12), `contract-summary.md` (C5).

## Cases (BR1)

- **BR1.1** `create_case` generates a unique case ID and stores the Patient, which is always synthetic. The default origin is `clinic`. When the origin is `benchmark`, a benchmarkRunId is required (FR12.2).
- **BR1.2** `search_patients` matches the query, case-insensitively, against the case ID, a finding name or a diagnosis label in the case's `pathway` messages. It returns only the owner's `clinic` cases, most recent first. An empty result is an empty list, and the UI then offers "Create new patient" (FR12.1, FR12.4, R-01).
- **BR1.3** `pin` is set when a walk starts and is never changed during the walk. `newer_version` returns the live version of the pinned pack when it is newer than the pin, and null otherwise (FR1.7).
- **BR1.4** `update_patient` accepts only sex, age, weightKg, pregnancyStatus, comorbidities, allergies and currentMedication. A weight must be between 0 and 400 kg. Every change is written to the audit as `patient_updated` (FR4.9).
- **BR1.5** Messages are append-only. A form message may move from `open` to `submitted` once, and submitting deletes its draft (FR5.8, FR12.3).

## Findings (BR2, FR4.11)

- **BR2.1** A metric finding is resolved against the pinned version's metric node (by name or synonym, through C1). A numeric value in the node unit is `ok`.
- **BR2.2** A value in a convertible unit is converted with U1's unit table. The finding stores the converted value and unit, and `enteredValue` keeps the original text, for example "102 g/L".
- **BR2.3** A non-numeric value, or a unit that can't be converted, is `invalid`.
- **BR2.4** A converted value outside the node's plausible range is `confirm_range`.
- **BR2.5** Two findings with the same metric name and different values are both `conflict`.
- **BR2.6** A non-metric finding (a symptom, for example), or a metric with no node, is `ok`. The grounding happens in U4.
- **BR2.7** A walk may start only when no finding is `invalid` or `conflict`. This is exposed as `findings_ready(caseId)`.

## Lock (BR3)

- **BR3.1** `acquire_lock` returns `held` when there is no lock, the lock is held by the same tab (the call refreshes the heartbeat), or the lock is older than 45 s. Otherwise it returns `read_only`.
- **BR3.2** `release_lock` removes the lock only when the tab holds it.

## Dose and safety (BR4)

- **BR4.1** `compute_dose` uses the drug node in effect after any edit. An `absolute` basis returns dose_value and unit. A `per_kg` basis needs weightKg and returns value × weight, rounded by the node's rounding rule, with the formula text "2.5 mg/kg × 58 kg = 145 mg". With no weight it returns MissingWeight (FR6.2).
- **BR4.2** `safety_checks` runs four checks per drug against the Patient (FR1.6):
  - **allergy:** for each patient allergy, find an allergy cross-reactivity node whose allergen_class matches. A conflict occurs when the drug's class is in conflicting_drug_classes.
  - **pregnancy:** when the patient is pregnant, a conflict occurs when the drug's contraindications include "pregnancy".
  - **interaction:** an interaction node whose pair (a, b) matches the drug or its class and a current medication or its class.
  - **duplicate_class:** another drug in the list, or a current medication, with the same drug class.
- **BR4.3** Each check is `conflict` when a cited node shows one. It is `ok` only when a node of that check's type exists for this drug or class and shows no conflict. In every other case it is `not_checked`, with the message "Not checked: no grounded safety data". A check is never `ok` without a node, and it carries the IDs of the nodes it used. Matching ignores case and surrounding spaces.
- **BR4.4** `apply_edit` checks the new values against the drug fields. When the drug changes, route, dose and frequency are reset to the new drug node's values (FR6.3). It stores a TreatmentEdit with the original values, writes `treatment_edited` to the audit (FR6.5), then returns the edit together with the re-run dose and safety results (FR6.4).

## Summary

There are 18 rules in four groups. Safety checks never claim "ok" without a node.
