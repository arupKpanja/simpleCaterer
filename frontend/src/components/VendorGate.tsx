import { useCallback, useEffect, useState } from "react";
import { decideVendorOrder, draftVendorOrder, getVendorOrder } from "../api";
import { currency, qty } from "../lib/format";
import { downloadCsv } from "../lib/export";
import type { VendorOrder } from "../types";

type Phase = "loading" | "idle" | "awaiting" | "working" | "placed" | "rejected" | "error";

function phaseFor(vo: VendorOrder | null): Phase {
  if (!vo) return "idle";
  if (vo.status === "placed") return "placed";
  if (vo.status === "rejected") return "rejected";
  return "awaiting"; // draft / awaiting_approval
}

export default function VendorGate({ orderId }: { orderId: string }) {
  const [vo, setVo] = useState<VendorOrder | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [err, setErr] = useState<string | null>(null);

  // Restore any existing vendor order when the approved order changes.
  useEffect(() => {
    let alive = true;
    setPhase("loading");
    setErr(null);
    getVendorOrder(orderId)
      .then((existing) => {
        if (!alive) return;
        setVo(existing);
        setPhase(phaseFor(existing));
      })
      .catch((e) => alive && (setErr(String(e.message ?? e)), setPhase("error")));
    return () => {
      alive = false;
    };
  }, [orderId]);

  const draft = useCallback(async () => {
    setPhase("working");
    setErr(null);
    try {
      const next = await draftVendorOrder(orderId);
      setVo(next);
      setPhase("awaiting");
    } catch (e) {
      setErr(String((e as Error).message ?? e));
      setPhase("error");
    }
  }, [orderId]);

  const decide = useCallback(
    async (decision: "approve" | "reject") => {
      setPhase("working");
      setErr(null);
      try {
        const next = await decideVendorOrder(orderId, decision);
        setVo(next);
        setPhase(phaseFor(next));
      } catch (e) {
        setErr(String((e as Error).message ?? e));
        setPhase("error");
      }
    },
    [orderId],
  );

  const shell =
    "rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900";

  if (phase === "loading") {
    return <section className={shell}><p className="text-sm text-slate-500">Loading vendor order…</p></section>;
  }

  return (
    <section className={shell}>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold">Supplier order</h2>
        {vo && (
          <span
            className={
              "rounded-full px-2 py-0.5 text-xs font-semibold uppercase " +
              (phase === "placed"
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                : phase === "rejected"
                  ? "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300"
                  : "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300")
            }
          >
            {phase === "awaiting" ? "awaiting approval" : phase}
          </span>
        )}
      </div>

      {err && (
        <p className="mb-3 rounded-lg border border-rose-200 bg-rose-50 p-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-300">
          {err}
        </p>
      )}

      {phase === "idle" && (
        <div>
          <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
            Draft a supplier order from this approved order. It pauses at a human
            approval gate — nothing is placed until you approve it.
          </p>
          <button
            onClick={draft}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-500"
          >
            Draft supplier order
          </button>
        </div>
      )}

      {(phase === "awaiting" || phase === "working") && vo && (
        <div>
          <LineTable
            head={["Item", "Qty", "Unit price", "Line cost"]}
            rows={vo.lines.map((l) => [
              l.item,
              `${qty(l.qty)} ${l.unit}`,
              currency(l.unit_price),
              currency(l.line_cost),
            ])}
            total={vo.total}
          />
          <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
            Placing the order deducts consumed stock and flags shortfalls.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => decide("approve")}
              disabled={phase === "working"}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
            >
              Approve &amp; place
            </button>
            <button
              onClick={() => decide("reject")}
              disabled={phase === "working"}
              className="rounded-lg border border-rose-300 px-4 py-2 text-sm font-semibold text-rose-600 transition hover:bg-rose-50 disabled:opacity-50 dark:border-rose-800 dark:hover:bg-rose-950/40"
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {phase === "placed" && vo && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-emerald-700 dark:text-emerald-400">
              ✓ Order placed. Exportable shopping list and stock impact below.
            </p>
            <div className="flex gap-2 no-print">
              <button
                onClick={() =>
                  downloadCsv(
                    `shopping-list-${vo.vendor_order_id.slice(0, 8)}.csv`,
                    ["Item", "Qty", "Unit", "Unit price", "Line cost"],
                    vo.shopping_list.map((l) => [l.item, l.qty, l.unit, l.unit_price, l.line_cost]),
                  )
                }
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Download CSV
              </button>
              <button
                onClick={() => window.print()}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Print
              </button>
            </div>
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold">Shopping list</h3>
            <LineTable
              head={["Item", "Qty", "Unit price", "Line cost"]}
              rows={vo.shopping_list.map((l) => [
                l.item,
                `${qty(l.qty)} ${l.unit}`,
                currency(l.unit_price),
                currency(l.line_cost),
              ])}
              total={vo.total}
            />
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold">Stock impact</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                    <th className="py-1 pr-3">Item</th>
                    <th className="py-1 pr-3">Required</th>
                    <th className="py-1 pr-3">Consumed</th>
                    <th className="py-1 pr-3">Short by</th>
                    <th className="py-1">Stock after</th>
                  </tr>
                </thead>
                <tbody>
                  {vo.stock_impact.map((s) => (
                    <tr key={s.item} className="border-t border-slate-100 dark:border-slate-800">
                      <td className="py-1 pr-3">{s.item}</td>
                      <td className="py-1 pr-3">{qty(s.required)}</td>
                      <td className="py-1 pr-3">{qty(s.consumed)}</td>
                      <td className={"py-1 pr-3 " + (s.short_by > 0 ? "font-medium text-amber-600 dark:text-amber-400" : "text-slate-400")}>
                        {qty(s.short_by)}
                      </td>
                      <td className="py-1">{qty(s.stock_after)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {phase === "rejected" && (
        <p className="text-sm text-rose-600 dark:text-rose-400">
          Order rejected — nothing was placed and stock was untouched.
        </p>
      )}
    </section>
  );
}

function LineTable({
  head,
  rows,
  total,
}: {
  head: string[];
  rows: string[][];
  total: number;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
            {head.map((h, i) => (
              <th key={h} className={"py-1 " + (i === head.length - 1 ? "text-right" : "pr-3")}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, ri) => (
            <tr key={ri} className="border-t border-slate-100 dark:border-slate-800">
              {r.map((c, ci) => (
                <td key={ci} className={"py-1 " + (ci === r.length - 1 ? "text-right" : "pr-3")}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
          <tr className="border-t border-slate-200 font-semibold dark:border-slate-700">
            <td className="py-1" colSpan={head.length - 1}>Total</td>
            <td className="py-1 text-right">{currency(total)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
