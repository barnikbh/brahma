// Forms Brahma posts into the chat (BR3.1, interaction-spec ChatForm, A4 input checks).
// A submitted form collapses to a one-line summary; on error it reopens with its entries.

import { useEffect, useId, useMemo, useRef, useState, type FormEvent } from "react";
import type { FormField, FormKind } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { FORM_TITLES, summarizeForm, type FormItemState } from "@/state/walkReducer";

export interface ChatFormProps {
  formKind: FormKind;
  fields: FormField[];
  state: FormItemState;
  summary: string | null;
  disabled?: boolean;
  onSubmit: (values: Record<string, unknown>, summary: string) => void;
  onCancel?: () => void;
}

export function ChatForm(props: ChatFormProps) {
  const headingId = useId();
  const title = FORM_TITLES[props.formKind];
  if (props.state === "submitted") {
    return (
      <div className="rounded-card border border-neutral-200 bg-white px-3 py-2 text-sm">
        <span className="text-xs text-ink-quiet">Brahma · form submitted · {title}</span>
        <p className="mt-0.5">
          <span aria-hidden="true">✓ </span>
          {props.summary ?? `${title} submitted`}
        </p>
      </div>
    );
  }
  return (
    <form
      aria-labelledby={headingId}
      className="rounded-card border-2 border-ink bg-white p-3"
      onSubmit={(e: FormEvent) => e.preventDefault()}
    >
      <p className="text-xs text-ink-quiet">form · needs your input</p>
      <h3 id={headingId} className="font-semibold">
        {title}
      </h3>
      <p className="sr-only" aria-live="polite">
        Brahma needs your input: {title}
      </p>
      {props.formKind === "confirm-findings" ? (
        <ConfirmFindings {...props} />
      ) : props.formKind === "needs-data" ? (
        <NeedsData {...props} />
      ) : (
        <ValueForm {...props} />
      )}
    </form>
  );
}

function numeric(value: unknown): boolean {
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value !== "string" || !value.trim()) return false;
  return Number.isFinite(Number(value));
}

interface Chip {
  key: string;
  field: FormField;
  value: string;
  unit: string;
  removed: boolean;
  confirmed: boolean;
}

function ConfirmFindings({ fields, state, disabled, onSubmit }: ChatFormProps) {
  const [chips, setChips] = useState<Chip[]>(() =>
    fields.map((field, i) => ({
      key: `${field.name}-${i}`,
      field,
      value: field.value === null || field.value === undefined ? "" : String(field.value),
      unit: field.unit ?? "",
      removed: false,
      confirmed: false,
    })),
  );
  // Conflicts: two values for one finding; the doctor picks one (A4).
  const conflictNames = useMemo(
    () =>
      Array.from(
        new Set(
          fields.filter((f) => f.validationState === "conflict").map((f) => f.name.toLowerCase()),
        ),
      ),
    [fields],
  );
  const [choice, setChoice] = useState<Record<string, string>>({});
  const firstInput = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    firstInput.current?.focus();
  }, []);

  const problem = (chip: Chip): string | null => {
    if (chip.removed) return null;
    const vs = chip.field.validationState;
    if (vs === "invalid" && !(chip.value !== String(chip.field.value ?? "") && numeric(chip.value)))
      return "Not a number or unit not recognised: fix or remove";
    if (vs === "confirm_range" && !chip.confirmed) return "Unusual value: confirm it";
    return null;
  };
  const unresolved =
    chips.some((c) => problem(c) !== null) || conflictNames.some((name) => !choice[name]);
  const locked = disabled || state === "submitting";

  const values = () => {
    const findings = chips
      .filter((c) => !c.removed)
      .filter((c) => {
        const name = c.field.name.toLowerCase();
        return !conflictNames.includes(name) || choice[name] === c.key;
      })
      .map((c) => ({
        kind: c.field.findingKind ?? "finding",
        name: c.field.name,
        value: c.value === "" ? null : numeric(c.value) ? Number(c.value) : c.value,
        unit: c.unit || null,
        duration: c.field.duration ?? null,
      }));
    return { findings };
  };

  const update = (key: string, patch: Partial<Chip>) =>
    setChips((all) => all.map((c) => (c.key === key ? { ...c, ...patch } : c)));

  return (
    <div className="mt-2 space-y-2">
      <p className="text-sm">I read these findings:</p>
      <ul className="space-y-1.5">
        {chips.map((chip, index) => {
          const issue = problem(chip);
          const conflict = chip.field.validationState === "conflict";
          const name = chip.field.name.toLowerCase();
          return (
            <li
              key={chip.key}
              className={chip.removed ? "text-ink-quiet line-through" : undefined}
              data-validation={chip.field.validationState ?? "ok"}
            >
              <div className="flex flex-wrap items-center gap-2">
                {conflict ? (
                  <input
                    type="radio"
                    name={`conflict-${name}`}
                    aria-label={`Use ${chip.field.name} ${chip.value} ${chip.unit}`}
                    checked={choice[name] === chip.key}
                    disabled={locked}
                    onChange={() => setChoice((c) => ({ ...c, [name]: chip.key }))}
                  />
                ) : null}
                <Badge variant="default">
                  <span className="text-ink-quiet">{chip.field.findingKind ?? "Finding"}</span>
                  <span>·</span>
                  <span>{chip.field.label}</span>
                  {chip.field.duration ? <span>({chip.field.duration})</span> : null}
                </Badge>
                {chip.field.value !== null && chip.field.value !== undefined ? (
                  <span className="flex items-center gap-1">
                    <Input
                      aria-label={`${chip.field.name} value`}
                      className="h-7 w-24"
                      value={chip.value}
                      disabled={locked || chip.removed}
                      onChange={(e) => update(chip.key, { value: e.target.value })}
                    />
                    <span className="text-xs">{chip.unit}</span>
                  </span>
                ) : null}
                <Button
                  ref={index === 0 ? firstInput : undefined}
                  size="sm"
                  variant="ghost"
                  disabled={locked}
                  onClick={() => update(chip.key, { removed: !chip.removed })}
                >
                  {chip.removed ? "Restore" : "Remove"}
                </Button>
              </div>
              {issue ? (
                <p className="mt-0.5 text-xs text-result-bad">
                  <span aria-hidden="true">! </span>
                  {issue}
                  {chip.field.validationState === "confirm_range" ? (
                    <label className="ml-2 inline-flex items-center gap-1 text-ink">
                      <input
                        type="checkbox"
                        checked={chip.confirmed}
                        disabled={locked}
                        onChange={(e) => update(chip.key, { confirmed: e.target.checked })}
                      />
                      Value is right
                    </label>
                  ) : null}
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
      {conflictNames.length > 0 ? (
        <p className="text-xs text-result-bad">
          <span aria-hidden="true">! </span>Two values for one finding: choose one.
        </p>
      ) : null}
      <Button
        type="submit"
        disabled={locked || unresolved}
        onClick={() => {
          const v = values();
          onSubmit(v, summarizeForm("confirm-findings", fields, v));
        }}
      >
        {state === "submitting" ? "Walking…" : "✓ Looks right — walk the graph"}
      </Button>
    </div>
  );
}

function NeedsData({ fields, state, disabled, onSubmit }: ChatFormProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const first = useRef<HTMLSelectElement | null>(null);
  useEffect(() => {
    first.current?.focus();
  }, []);
  const locked = disabled || state === "submitting";
  return (
    <div className="mt-2 space-y-2">
      <p className="text-sm">To refine this, enter the results you have. You can leave some out.</p>
      {fields.map((field, index) => {
        const id = `nd-${field.name}`;
        return (
          <div key={field.name} className="grid grid-cols-[1fr_200px] items-center gap-2">
            <label htmlFor={id} className="text-sm">
              {field.label}
              {field.nodeId ? (
                <span className="ml-1 font-mono text-[11px] text-brand-700">{field.nodeId}</span>
              ) : null}
            </label>
            {field.options && field.options.length > 0 ? (
              <Select
                id={id}
                ref={index === 0 ? first : undefined}
                value={values[field.name] ?? ""}
                disabled={locked}
                onChange={(e) => setValues((v) => ({ ...v, [field.name]: e.target.value }))}
              >
                <option value="">? Not yet tested</option>
                {field.options.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                id={id}
                value={values[field.name] ?? ""}
                disabled={locked}
                onChange={(e) => setValues((v) => ({ ...v, [field.name]: e.target.value }))}
              />
            )}
          </div>
        );
      })}
      <Button
        type="submit"
        disabled={locked}
        onClick={() => {
          const filled = Object.fromEntries(
            Object.entries(values).filter(([, v]) => v.trim() !== ""),
          );
          onSubmit(filled, summarizeForm("needs-data", fields, filled));
        }}
      >
        {state === "submitting" ? "Walking…" : "Submit results"}
      </Button>
    </div>
  );
}

/** Edit treatment and patient details: one text field per value. */
function ValueForm({ formKind, fields, state, disabled, onSubmit, onCancel }: ChatFormProps) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(fields.map((f) => [f.name, f.value == null ? "" : String(f.value)])),
  );
  const locked = disabled || state === "submitting";
  const changed = () =>
    Object.fromEntries(
      fields
        .filter((f) => (values[f.name] ?? "") !== (f.value == null ? "" : String(f.value)))
        .map((f) => [f.name, numeric(values[f.name]) ? Number(values[f.name]) : values[f.name]]),
    );
  return (
    <div className="mt-2 space-y-2">
      {fields.map((field) => (
        <label key={field.name} className="grid grid-cols-[140px_1fr] items-center gap-2 text-sm">
          {field.label}
          <Input
            value={values[field.name] ?? ""}
            disabled={locked}
            onChange={(e) => setValues((v) => ({ ...v, [field.name]: e.target.value }))}
          />
        </label>
      ))}
      <div className="flex gap-2">
        <Button
          type="submit"
          disabled={locked}
          onClick={() => {
            const v = changed();
            onSubmit(v, summarizeForm(formKind, fields, v));
          }}
        >
          {state === "submitting" ? "Applying…" : "Apply"}
        </Button>
        {onCancel ? (
          <Button variant="outline" disabled={state === "submitting"} onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
      </div>
    </div>
  );
}
