import { useState } from "react";
import type { Requirements } from "../types";

// Chip label -> restriction phrase the backend parser understands.
const DIET_OPTIONS: { label: string; value: string }[] = [
  { label: "Vegetarian", value: "vegetarian" },
  { label: "Vegan", value: "vegan" },
  { label: "Gluten-free", value: "gluten free" },
  { label: "No nuts", value: "no nuts" },
  { label: "No dairy", value: "no dairy" },
  { label: "No shellfish", value: "no shellfish" },
];

const CUISINES = ["Indian", "Continental", "Any"];

interface FormState {
  event_type: string;
  guest_count: string; // kept as string for controlled input
  budget: string;
  cuisine_pref: string;
  event_date: string;
  location: string;
  diet: string[];
}

const EMPTY: FormState = {
  event_type: "",
  guest_count: "",
  budget: "",
  cuisine_pref: "Indian",
  event_date: "",
  location: "",
  diet: [],
};

const SAMPLE: FormState = {
  event_type: "wedding reception",
  guest_count: "150",
  budget: "400000",
  cuisine_pref: "Indian",
  event_date: "",
  location: "",
  diet: ["vegetarian", "no nuts"],
};

type Errors = Partial<Record<"event_type" | "guest_count" | "budget", string>>;

function validate(s: FormState): Errors {
  const e: Errors = {};
  if (!s.event_type.trim()) e.event_type = "Event type is required.";
  const guests = Number(s.guest_count);
  if (!s.guest_count.trim() || !Number.isFinite(guests) || guests <= 0)
    e.guest_count = "Enter a guest count greater than 0.";
  if (s.budget.trim()) {
    const b = Number(s.budget);
    if (!Number.isFinite(b) || b < 0) e.budget = "Budget must be 0 or more.";
  }
  return e;
}

export default function RequirementsForm({
  onSubmit,
  busy = false,
}: {
  onSubmit: (reqs: Requirements) => void;
  busy?: boolean;
}) {
  const [s, setS] = useState<FormState>(EMPTY);
  const [touched, setTouched] = useState(false);
  const errors = validate(s);
  const isValid = Object.keys(errors).length === 0;

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setS((prev) => ({ ...prev, [k]: v }));

  const toggleDiet = (value: string) =>
    setS((prev) => ({
      ...prev,
      diet: prev.diet.includes(value)
        ? prev.diet.filter((d) => d !== value)
        : [...prev.diet, value],
    }));

  const submit = (ev: React.FormEvent) => {
    ev.preventDefault();
    setTouched(true);
    if (!isValid) return;
    onSubmit({
      event_type: s.event_type.trim(),
      guest_count: Number(s.guest_count),
      budget: s.budget.trim() ? Number(s.budget) : 0,
      dietary_restrictions: s.diet,
      cuisine_pref: s.cuisine_pref === "Any" ? "" : s.cuisine_pref,
      location: s.location.trim(),
      event_date: s.event_date,
    });
  };

  const field =
    "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/30 dark:border-slate-700 dark:bg-slate-900";
  const label = "mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300";
  const err = "mt-1 text-xs text-rose-600 dark:text-rose-400";
  const showErr = (k: keyof Errors) => touched && errors[k];

  return (
    <form
      onSubmit={submit}
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold">Event requirements</h2>
        <button
          type="button"
          onClick={() => { setS(SAMPLE); setTouched(false); }}
          className="text-xs font-medium text-sky-600 hover:underline dark:text-sky-400"
        >
          Fill sample
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className={label} htmlFor="event_type">Event type</label>
          <input
            id="event_type"
            className={field}
            placeholder="e.g. wedding reception"
            value={s.event_type}
            onChange={(e) => set("event_type", e.target.value)}
          />
          {showErr("event_type") && <p className={err}>{errors.event_type}</p>}
        </div>

        <div>
          <label className={label} htmlFor="guest_count">Guest count</label>
          <input
            id="guest_count"
            type="number"
            min={1}
            className={field}
            placeholder="120"
            value={s.guest_count}
            onChange={(e) => set("guest_count", e.target.value)}
          />
          {showErr("guest_count") && <p className={err}>{errors.guest_count}</p>}
        </div>

        <div>
          <label className={label} htmlFor="budget">Budget (total, $)</label>
          <input
            id="budget"
            type="number"
            min={0}
            className={field}
            placeholder="0 = no limit"
            value={s.budget}
            onChange={(e) => set("budget", e.target.value)}
          />
          {showErr("budget") && <p className={err}>{errors.budget}</p>}
        </div>

        <div>
          <label className={label} htmlFor="cuisine">Cuisine</label>
          <select
            id="cuisine"
            className={field}
            value={s.cuisine_pref}
            onChange={(e) => set("cuisine_pref", e.target.value)}
          >
            {CUISINES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div>
          <label className={label} htmlFor="event_date">Event date</label>
          <input
            id="event_date"
            type="date"
            className={field}
            value={s.event_date}
            onChange={(e) => set("event_date", e.target.value)}
          />
        </div>

        <div className="sm:col-span-2">
          <label className={label} htmlFor="location">Location</label>
          <input
            id="location"
            className={field}
            placeholder="optional"
            value={s.location}
            onChange={(e) => set("location", e.target.value)}
          />
        </div>

        <div className="sm:col-span-2">
          <span className={label}>Dietary restrictions</span>
          <div className="flex flex-wrap gap-2">
            {DIET_OPTIONS.map((d) => {
              const active = s.diet.includes(d.value);
              return (
                <button
                  key={d.value}
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggleDiet(d.value)}
                  className={
                    "rounded-full border px-3 py-1.5 text-sm transition " +
                    (active
                      ? "border-sky-500 bg-sky-500 text-white shadow-sm"
                      : "border-slate-300 bg-white text-slate-600 hover:border-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300")
                  }
                >
                  {d.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-5 flex items-center justify-between">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Allergen &amp; budget rules are enforced server-side.
        </p>
        <button
          type="submit"
          disabled={busy || (touched && !isValid)}
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Planning…" : "Generate options"}
        </button>
      </div>
    </form>
  );
}
