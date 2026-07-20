import { useState } from "react";
import { currency, qty } from "../lib/format";
import type { Option } from "../types";

const TIER_ACCENT: Record<string, string> = {
  essential: "border-sky-300 dark:border-sky-800",
  standard: "border-violet-300 dark:border-violet-800",
  premium: "border-amber-300 dark:border-amber-800",
};
const TIER_BADGE: Record<string, string> = {
  essential: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  standard: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  premium: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
};

function AllergenPills({ allergens }: { allergens: string[] }) {
  if (!allergens.length) return null;
  return (
    <span className="flex flex-wrap gap-1">
      {allergens.map((a) => (
        <span
          key={a}
          className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-700 dark:bg-amber-950/60 dark:text-amber-300"
        >
          {a}
        </span>
      ))}
    </span>
  );
}

export default function OptionCard({
  option,
  recommended = false,
  onSelect,
  selecting = false,
}: {
  option: Option;
  recommended?: boolean;
  onSelect?: (o: Option) => void;
  selecting?: boolean;
}) {
  const [showList, setShowList] = useState(false);
  const accent = TIER_ACCENT[option.tier] ?? "border-slate-300";
  const badge = TIER_BADGE[option.tier] ?? "bg-slate-100 text-slate-700";

  return (
    <div
      className={`relative flex flex-col rounded-xl border-2 ${accent} bg-white shadow-sm dark:bg-slate-900`}
    >
      {recommended && (
        <span className="absolute -top-2.5 left-4 rounded-full bg-violet-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
          Recommended
        </span>
      )}

      <div className="border-b border-slate-100 p-4 dark:border-slate-800">
        <div className="flex items-center justify-between">
          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${badge}`}>
            {option.tier}
          </span>
          <div className="flex items-center gap-1.5">
            {option.allergen_safe ? (
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                Allergen-safe
              </span>
            ) : (
              <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-medium text-rose-700 dark:bg-rose-950 dark:text-rose-300">
                Allergen risk
              </span>
            )}
          </div>
        </div>
        <h3 className="mt-2 text-base font-semibold">{option.theme}</h3>
      </div>

      {/* Menu */}
      <div className="flex-1 space-y-2 p-4">
        {option.courses.map((c) => (
          <div key={c.course} className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-[11px] uppercase tracking-wide text-slate-400">{c.course}</p>
              <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{c.dish}</p>
            </div>
            <AllergenPills allergens={c.allergens} />
          </div>
        ))}

        <div className="!mt-4 space-y-1 border-t border-slate-100 pt-3 text-sm dark:border-slate-800">
          <div className="flex justify-between text-slate-600 dark:text-slate-300">
            <span>Decor · {option.decor.name || "—"}</span>
            <span>{currency(option.decor_cost)}</span>
          </div>
          <div className="flex justify-between text-slate-600 dark:text-slate-300">
            <span>Venue · {option.venue.name || "—"}</span>
            <span>{currency(option.venue_cost)}</span>
          </div>
          <div className="flex justify-between text-slate-600 dark:text-slate-300">
            <span>Food (ingredients)</span>
            <span>{currency(option.food_cost)}</span>
          </div>
        </div>
      </div>

      {/* Totals */}
      <div className="border-t border-slate-100 p-4 dark:border-slate-800">
        <div className="flex items-end justify-between">
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400">Total</p>
            <p className="text-xl font-bold">{currency(option.total_cost)}</p>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {currency(option.per_guest)}/guest
          </p>
        </div>

        <div className="mt-2">
          {option.within_budget ? (
            <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
              ✓ Within budget
            </span>
          ) : (
            <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
              ⚠ Over budget by {currency(option.overage)}
            </span>
          )}
        </div>

        <button
          onClick={() => setShowList((v) => !v)}
          className="mt-3 text-xs font-medium text-sky-600 hover:underline dark:text-sky-400"
          aria-expanded={showList}
        >
          {showList ? "Hide" : "Show"} shopping list ({option.shopping_list.length})
        </button>
        {showList && (
          <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto text-xs">
            {option.shopping_list.map((l) => (
              <li key={l.item} className="flex justify-between gap-2">
                <span className="truncate text-slate-600 dark:text-slate-300">
                  {l.item} · {qty(l.qty)} {l.unit}
                  {l.short_by > 0 && (
                    <span className="ml-1 text-amber-600 dark:text-amber-400">
                      (short {qty(l.short_by)})
                    </span>
                  )}
                </span>
                <span className="shrink-0 text-slate-500">{currency(l.line_cost)}</span>
              </li>
            ))}
          </ul>
        )}

        {onSelect && (
          <button
            onClick={() => onSelect(option)}
            disabled={selecting}
            className="mt-4 w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-200"
          >
            {selecting ? "Freezing…" : "Choose this option"}
          </button>
        )}
      </div>
    </div>
  );
}
