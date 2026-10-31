import { useState, type FormEvent } from "react";
import { ApiError, api } from "@/api/client";
import type { CaseView, Sex } from "@/api/types";
import { Synthetic } from "@/components/Synthetic";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { splitList } from "@/lib/utils";

/** The sticky patient card (BR3.5) with the patient-details form (FR4.9). */
export function PatientCard({
  view,
  readOnly,
  onExit,
  onUpdated,
}: {
  view: CaseView;
  readOnly: boolean;
  onExit: () => void;
  onUpdated: (view: CaseView) => void;
}) {
  const { patient } = view;
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const initials = patient.syntheticName
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const comorbidities = patient.comorbidities ?? [];
  const allergies = patient.allergies ?? [];

  return (
    <div className="sticky top-0 z-20 rounded-card border border-neutral-300 bg-white px-4 py-2">
      <div className="flex flex-wrap items-center gap-3">
        <span
          aria-hidden="true"
          className="flex h-9 w-9 items-center justify-center rounded-full bg-neutral-200 text-sm"
        >
          {initials}
        </span>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <strong>
              <Synthetic>{patient.syntheticName}</Synthetic>
            </strong>
            <span>
              {patient.age} y ·{" "}
              {patient.sex === "female"
                ? "Female"
                : patient.sex === "male"
                  ? "Male"
                  : "Sex unknown"}
              {patient.weightKg ? ` · ${patient.weightKg} kg` : ""}
            </span>
            <span className="font-mono text-xs text-ink-quiet" data-testid="case-id">
              {view.case.caseId} · synthetic
            </span>
          </div>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {comorbidities[0] ? <Badge>Comorbidities: {comorbidities[0]}</Badge> : null}
            {allergies.map((a) => (
              <Badge key={a} variant="bad">
                <span aria-hidden="true">⚠</span> Allergy: {a}
              </Badge>
            ))}
            {expanded ? (
              comorbidities.slice(1).map((c) => <Badge key={c}>{c}</Badge>)
            ) : comorbidities.length > 1 ? (
              <Badge variant="quiet">+{comorbidities.length - 1} more</Badge>
            ) : null}
            {expanded && (patient.currentMedication ?? []).length > 0 ? (
              <Badge>Medication: {(patient.currentMedication ?? []).join(", ")}</Badge>
            ) : null}
          </div>
        </div>
        <div className="ml-auto flex gap-2">
          <Button size="sm" variant="outline" disabled={readOnly} onClick={() => setEditing(true)}>
            Edit details
          </Button>
          <Button
            size="sm"
            variant="outline"
            aria-expanded={expanded}
            onClick={() => setExpanded((e) => !e)}
          >
            {expanded ? "Collapse ▴" : "Expand ▾"}
          </Button>
          <Button size="sm" variant="outline" onClick={onExit}>
            Exit case
          </Button>
        </div>
      </div>
      {editing ? (
        <DetailsForm
          view={view}
          onCancel={() => setEditing(false)}
          onSaved={(next) => {
            setEditing(false);
            onUpdated(next);
          }}
        />
      ) : null}
    </div>
  );
}

function DetailsForm({
  view,
  onCancel,
  onSaved,
}: {
  view: CaseView;
  onCancel: () => void;
  onSaved: (view: CaseView) => void;
}) {
  const p = view.patient;
  const [sex, setSex] = useState<Sex>(p.sex);
  const [weight, setWeight] = useState(p.weightKg ? String(p.weightKg) : "");
  const [allergies, setAllergies] = useState((p.allergies ?? []).join(", "));
  const [comorbidities, setComorbidities] = useState((p.comorbidities ?? []).join(", "));
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      onSaved(
        await api.changePatient(view.case.caseId, {
          sex,
          weightKg: weight.trim() ? Number(weight) : null,
          allergies: splitList(allergies),
          comorbidities: splitList(comorbidities),
        }),
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The details could not be saved.");
    }
  };

  return (
    <form
      aria-label="Patient details"
      onSubmit={(e) => void submit(e)}
      className="mt-2 grid grid-cols-4 gap-2 border-t border-neutral-200 pt-2 text-sm"
    >
      <label>
        Sex
        <Select value={sex} onChange={(e) => setSex(e.target.value as Sex)}>
          <option value="female">Female</option>
          <option value="male">Male</option>
          <option value="unknown">Unknown</option>
        </Select>
      </label>
      <label>
        Weight (kg)
        <Input
          type="number"
          min={1}
          step="0.1"
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
        />
      </label>
      <label>
        Allergies
        <Input value={allergies} onChange={(e) => setAllergies(e.target.value)} />
      </label>
      <label>
        Comorbidities
        <Input value={comorbidities} onChange={(e) => setComorbidities(e.target.value)} />
      </label>
      {error ? <p className="col-span-4 text-result-bad">! {error}</p> : null}
      <div className="col-span-4 flex gap-2">
        <Button type="submit" size="sm">
          Save details
        </Button>
        <Button size="sm" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
