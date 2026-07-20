import { currency } from "../lib/format";
import type { ApprovedOrder } from "../types";
import OptionCard from "./OptionCard";

export default function ApprovedOrderPanel({ order }: { order: ApprovedOrder }) {
  const when = new Date(order.approved_at).toLocaleString();
  return (
    <section className="rounded-xl border-2 border-emerald-300 bg-emerald-50/40 p-5 dark:border-emerald-800 dark:bg-emerald-950/20">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">
            Approved order —{" "}
            <span className="capitalize">{order.tier}</span> tier
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Frozen {when} · {order.guest_count} guests · order{" "}
            <code className="text-xs">{order.order_id.slice(0, 8)}</code>
          </p>
        </div>
        <div className="text-right">
          <span className="rounded-full bg-emerald-600 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">
            {order.status}
          </span>
          <p className="mt-1 text-sm font-semibold">
            {currency(order.total_cost)}{" "}
            <span className="font-normal text-slate-500 dark:text-slate-400">
              ({currency(order.per_guest)}/guest)
            </span>
          </p>
        </div>
      </div>

      <div className="max-w-sm">
        <OptionCard option={order.snapshot} />
      </div>

      <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
        This option is now the immutable baseline. Draft and approve the supplier
        order below.
      </p>
    </section>
  );
}
