"""Dose computation and safety checks (rules.md BR4.1-BR4.4, FR1.6, FR6).

Pure functions over one version's nodes (``NodeCatalog``) and the patient, so U4's
grounding guard can call them directly. A check is ``conflict`` when a cited node shows
one and ``ok`` only when a node of that check's type exists for this drug and shows
none; in every other case it is ``not_checked``. ``SafetyResult`` itself refuses an
``ok`` without a node.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import ValidationError
from pydantic.alias_generators import to_camel

from brahma.cases.catalog import NodeCatalog
from brahma.cases.errors import InvalidTreatmentEdit, NotADrugNode
from brahma.cases.findings import format_decimal
from brahma.cases.models import (
    NOT_CHECKED_MESSAGE,
    DoseResult,
    MissingWeight,
    Patient,
    SafetyCheck,
    SafetyResult,
)
from brahma.knowledge.matcher import normalise_text
from brahma.knowledge.models import AllergyCrossReactivityFields, DrugFields, InteractionFields
from brahma.knowledge.models import Node as KgNode
from brahma.knowledge.units import to_decimal

DRUG_NODE_KEY = "drugNodeId"
EDITABLE_FIELDS = ("drug", "route", "doseValue", "doseUnit", "doseBasis", "frequency", "duration")
RESET_ON_DRUG_CHANGE = ("route", "doseValue", "doseUnit", "doseBasis", "frequency", "duration")
PREGNANT = frozenset({"pregnant", "yes", "true"})
NOT_PREGNANT = frozenset({"not pregnant", "not_pregnant", "no", "false"})
_NEAREST = re.compile(r"nearest\s+(\d+(?:\.\d+)?)", re.IGNORECASE)


@dataclass(frozen=True)
class EffectiveDrug:
    """A drug as it stands for a case: the requested node, the node whose values are used
    (another drug node after a drug change) and the values after any edit."""

    node_id: str
    drug_node_id: str
    fields: DrugFields


# --- effective values and edits (BR4.4) ---------------------------------------------------


def drug_fields(node: KgNode) -> DrugFields:
    """The node's drug fields; raises NotADrugNode for any other node type."""
    if node.type != "drug":
        raise NotADrugNode(node.node_id)
    return DrugFields.model_validate(node.fields)


def effective_drug(
    node: KgNode, edit_values: dict[str, Any] | None, catalog: NodeCatalog
) -> EffectiveDrug:
    """The drug values in effect: the node's, or the latest edit's snapshot over them."""
    fields = drug_fields(node)
    if not edit_values:
        return EffectiveDrug(node.node_id, node.node_id, fields)
    base_id = str(edit_values.get(DRUG_NODE_KEY, node.node_id))
    base = catalog.get(base_id)
    merged = {**base.fields, **{k: v for k, v in edit_values.items() if k != DRUG_NODE_KEY}}
    return EffectiveDrug(node.node_id, base_id, DrugFields.model_validate(merged))


def edit_snapshot(drug: EffectiveDrug) -> dict[str, Any]:
    """The editable values of a drug, plus the node they come from."""
    dumped = drug.fields.model_dump(by_alias=True)
    return {DRUG_NODE_KEY: drug.drug_node_id, **{k: dumped[k] for k in EDITABLE_FIELDS}}


def _camel_keys(values: dict[str, Any]) -> dict[str, Any]:
    camel = {to_camel(k): v for k, v in values.items()}
    unknown = sorted(set(camel) - set(EDITABLE_FIELDS))
    if unknown:
        raise InvalidTreatmentEdit(f"fields that cannot be edited: {', '.join(unknown)}")
    if not camel:
        raise InvalidTreatmentEdit("an edit must change at least one field")
    return camel


def resolve_edit(
    current: EffectiveDrug, new_values: dict[str, Any], catalog: NodeCatalog
) -> dict[str, Any]:
    """Check an edit against the drug fields and return the full snapshot to store.

    When the drug changes, route, dose and frequency reset to the new drug node's values
    (FR6.3); any other values sent with the change are not applied.
    """
    values = _camel_keys(new_values)
    drug_name = values.get("drug")
    if drug_name is not None and normalise_text(str(drug_name)) != normalise_text(
        current.fields.drug
    ):
        target = catalog.drug(str(drug_name))
        if target is None:
            raise InvalidTreatmentEdit("the new drug has no drug node in this pack version")
        return edit_snapshot(EffectiveDrug(current.node_id, target.node_id, drug_fields(target)))
    merged = {**current.fields.model_dump(by_alias=True), **values}
    if merged["doseBasis"] == "weight_band" and "doseValue" in values:
        # compute_dose reads the bands, so a new value here would be silently ignored.
        raise InvalidTreatmentEdit("this dose follows weight bands; set a fixed dose basis first")
    try:
        fields = DrugFields.model_validate(merged)
    except ValidationError as exc:
        names = sorted({str(err["loc"][0]) for err in exc.errors() if err["loc"]})
        raise InvalidTreatmentEdit(f"invalid values for: {', '.join(names)}") from None
    return edit_snapshot(EffectiveDrug(current.node_id, current.drug_node_id, fields))


# --- dose (BR4.1) -------------------------------------------------------------------------


def _round(value: Decimal, rounding: str) -> Decimal:
    match = _NEAREST.search(rounding)
    if match is None:
        return value
    step = Decimal(match.group(1))
    if step == 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_HALF_UP) * step


def compute_dose(drug: EffectiveDrug, weight_kg: float | None) -> DoseResult | MissingWeight:
    """The dose with its formula text; MissingWeight for a per-kg dose with no weight."""
    f = drug.fields
    dose = to_decimal(f.dose_value)
    if dose is None:
        raise InvalidTreatmentEdit("dose value is not a number")
    cited = [drug.drug_node_id]
    if f.dose_basis == "absolute":
        formula = f"{format_decimal(dose)} {f.dose_unit} (fixed dose)"
        return DoseResult(value=float(dose), unit=f.dose_unit, formula=formula, node_ids=cited)
    weight = to_decimal(weight_kg)
    if f.dose_basis == "weight_band":
        if weight is None:
            return MissingWeight(
                node_id=drug.drug_node_id, message="Weight needed to pick the weight-band dose"
            )
        band = f.band_for(weight)
        amount = format_decimal(Decimal(str(band.dose_value)))
        formula = f"{amount} {band.dose_unit} for {format_decimal(weight)} kg (weight band)"
        return DoseResult(
            value=float(band.dose_value), unit=band.dose_unit, formula=formula, node_ids=cited
        )
    if weight is None:
        return MissingWeight(node_id=drug.drug_node_id)
    unit = re.sub(r"/\s*kg$", "", f.dose_unit.strip(), flags=re.IGNORECASE)
    exact = dose * weight
    total = _round(exact, f.rounding)
    formula = (
        f"{format_decimal(dose)} {unit}/kg × {format_decimal(weight)} kg = "
        f"{format_decimal(exact)} {unit}"
    )
    if total != exact:
        formula += f", rounded to {format_decimal(total)} {unit}"
    return DoseResult(value=float(total), unit=unit, formula=formula, node_ids=cited)


# --- safety (BR4.2, BR4.3) ----------------------------------------------------------------


def _result(
    check: SafetyCheck, drug: EffectiveDrug, status: str, node_ids: list[str], message: str
) -> SafetyResult:
    return SafetyResult.model_validate(
        {
            "check": check,
            "status": status,
            "nodeIds": list(dict.fromkeys(node_ids)),
            "message": message,
            "drugNodeId": drug.node_id,
        }
    )


def _not_checked(check: SafetyCheck, drug: EffectiveDrug) -> SafetyResult:
    return _result(check, drug, "not_checked", [], NOT_CHECKED_MESSAGE)


def _terms(fields: DrugFields) -> set[str]:
    return {normalise_text(t) for t in (fields.drug, *fields.synonyms, fields.drug_class)}


def _allergy(drug: EffectiveDrug, patient: Patient, catalog: NodeCatalog) -> SafetyResult:
    allergies = [a for a in patient.allergies if a.strip()]
    drug_class = normalise_text(drug.fields.drug_class)
    used: list[str] = []
    conflicts: list[str] = []
    unmatched = False
    for allergy in allergies:
        nodes = catalog.allergy_nodes(allergy)
        unmatched = unmatched or not nodes
        for node in nodes:
            used.append(node.node_id)
            classes = AllergyCrossReactivityFields.model_validate(node.fields)
            if drug_class in {normalise_text(c) for c in classes.conflicting_drug_classes}:
                conflicts.append(node.node_id)
    if conflicts:
        message = f"Allergy conflict: {drug.fields.drug_class} cross-reacts with a recorded allergy"
        return _result("allergy", drug, "conflict", [*conflicts, drug.drug_node_id], message)
    if unmatched or not used:
        return _not_checked("allergy", drug)
    return _result("allergy", drug, "ok", used, "No cross-reactivity with recorded allergies")


def _pregnancy(drug: EffectiveDrug, patient: Patient) -> SafetyResult:
    status = normalise_text(patient.pregnancy_status or "")
    if patient.sex == "male" or status in NOT_PREGNANT:
        return _result("pregnancy", drug, "ok", [drug.drug_node_id], "Patient is not pregnant")
    if status not in PREGNANT:
        return _not_checked("pregnancy", drug)
    contraindications = {normalise_text(c) for c in drug.fields.contraindications}
    if "pregnancy" in contraindications:
        message = f"Pregnancy conflict: {drug.fields.drug} is contraindicated in pregnancy"
        return _result("pregnancy", drug, "conflict", [drug.drug_node_id], message)
    return _not_checked("pregnancy", drug)


def _medication_terms(patient: Patient, catalog: NodeCatalog) -> set[str]:
    terms: set[str] = set()
    for medication in patient.current_medication:
        terms.add(normalise_text(medication))
        node = catalog.drug(medication)
        if node is not None:
            terms |= _terms(drug_fields(node))
    return terms


def _interaction(drug: EffectiveDrug, patient: Patient, catalog: NodeCatalog) -> SafetyResult:
    own = _terms(drug.fields)
    nodes: list[tuple[str, InteractionFields]] = []
    for node in catalog.of_type("interaction"):
        pair = InteractionFields.model_validate(node.fields)
        if normalise_text(pair.a) in own or normalise_text(pair.b) in own:
            nodes.append((node.node_id, pair))
    if not nodes:
        return _not_checked("interaction", drug)
    meds = _medication_terms(patient, catalog)
    conflicts = [
        node_id
        for node_id, pair in nodes
        if (normalise_text(pair.a) in own and normalise_text(pair.b) in meds)
        or (normalise_text(pair.b) in own and normalise_text(pair.a) in meds)
    ]
    if conflicts:
        message = f"Interaction: {drug.fields.drug} interacts with a current medication"
        return _result("interaction", drug, "conflict", conflicts, message)
    used = [node_id for node_id, _ in nodes]
    return _result("interaction", drug, "ok", used, "No interaction with current medication")


def _duplicate_class(
    drug: EffectiveDrug, others: list[EffectiveDrug], patient: Patient, catalog: NodeCatalog
) -> SafetyResult:
    drug_class = normalise_text(drug.fields.drug_class)
    compared: list[tuple[str, DrugFields]] = [
        (o.drug_node_id, o.fields) for o in others if o.drug_node_id != drug.drug_node_id
    ]
    unresolved = False
    for medication in patient.current_medication:
        node = catalog.drug(medication)
        if node is None:
            unresolved = True
        elif node.node_id != drug.drug_node_id:
            compared.append((node.node_id, drug_fields(node)))
    same = [i for i, f in compared if normalise_text(f.drug_class) == drug_class]
    if same:
        message = f"Duplicate class: another {drug.fields.drug_class} is listed or being taken"
        return _result("duplicate_class", drug, "conflict", [drug.drug_node_id, *same], message)
    if unresolved:
        return _not_checked("duplicate_class", drug)
    used = [drug.drug_node_id, *(i for i, _ in compared)]
    return _result("duplicate_class", drug, "ok", used, "No other drug of the same class")


def safety_checks(
    drugs: list[EffectiveDrug], patient: Patient, catalog: NodeCatalog
) -> list[SafetyResult]:
    """The four checks for each drug, in order: allergy, pregnancy, interaction, duplicate."""
    results: list[SafetyResult] = []
    for drug in drugs:
        results.append(_allergy(drug, patient, catalog))
        results.append(_pregnancy(drug, patient))
        results.append(_interaction(drug, patient, catalog))
        results.append(_duplicate_class(drug, drugs, patient, catalog))
    return results
