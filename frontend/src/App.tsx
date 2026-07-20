import { useEffect, useRef, useState } from "react";
import { AlreadyApprovedError, approveOrder, getOptions, getOrder } from "./api";
import ApprovedOrderPanel from "./components/ApprovedOrderPanel";
import ConstraintsBanner from "./components/ConstraintsBanner";
import VendorGate from "./components/VendorGate";
import HealthBadge from "./components/HealthBadge";
import OptionsGrid from "./components/OptionsGrid";
import RequirementsForm from "./components/RequirementsForm";
import StageTimeline from "./components/StageTimeline";
import ThemeToggle from "./components/ThemeToggle";
import { usePlan } from "./hooks/usePlan";
import type { ApprovedOrder, Option, Requirements } from "./types";

/** Reflect the current event/session/order in the URL without navigating. */
function syncUrl(params: Record<string, string | undefined>) {
  const usp = new URLSearchParams(window.location.search);
  for (const [k, v] of Object.entries(params)) {
    if (v) usp.set(k, v);
    else usp.delete(k);
  }
  const qs = usp.toString();
  window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
}

export default function App() {
  const plan = usePlan();
  const busy = plan.status === "streaming";
  const options = plan.result?.options ?? [];
  const resultErrors = plan.result?.errors ?? [];
  const eventId = plan.result?.event_id;

  const [order, setOrder] = useState<ApprovedOrder | null>(null);
  const [selecting, setSelecting] = useState<string | null>(null);
  const [approveErr, setApproveErr] = useState<string | null>(null);
  const [restored, setRestored] = useState(false);
  const [reqs, setReqs] = useState<Requirements | null>(null);
  const bootstrapped = useRef(false);

  // Restore a previous session from the URL on first load.
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const ev = p.get("event");
    const sid = p.get("session") ?? "";
    const oid = p.get("order");
    const tasks: Promise<unknown>[] = [];
    if (ev) {
      tasks.push(
        getOptions(ev)
          .then((se) => {
            plan.hydrate({
              type: "result",
              session_id: sid,
              event_id: se.event_id,
              options: se.options,
              errors: [],
              log: [],
            });
            setReqs(se.requirements);
            setRestored(true);
          })
          .catch(() => {}),
      );
    }
    if (oid) tasks.push(getOrder(oid).then(setOrder).catch(() => {}));
    Promise.allSettled(tasks).finally(() => (bootstrapped.current = true));
    if (!ev && !oid) bootstrapped.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the URL in sync with the current event/session/order.
  useEffect(() => {
    if (!bootstrapped.current) return;
    syncUrl({
      event: plan.result?.event_id,
      session: plan.result?.session_id || undefined,
      order: order?.order_id,
    });
  }, [plan.result?.event_id, plan.result?.session_id, order?.order_id]);

  const startPlan = (next: Requirements) => {
    setRestored(false);
    setOrder(null);
    setApproveErr(null);
    setReqs(next);
    plan.run(next);
  };

  const clearAll = () => {
    setOrder(null);
    setApproveErr(null);
    setReqs(null);
    plan.reset();
  };

  const choose = async (o: Option) => {
    if (!eventId || !o.id) {
      setApproveErr("Missing event or option id — can’t freeze this option.");
      return;
    }
    setSelecting(o.tier);
    setApproveErr(null);
    try {
      setOrder(await approveOrder(eventId, o.id));
    } catch (e) {
      if (e instanceof AlreadyApprovedError) {
        const existing = await getOrder(e.orderId).catch(() => null);
        if (existing) {
          setOrder(existing);
          setApproveErr("This event was already approved — showing the frozen order.");
        } else {
          setApproveErr(e.message);
        }
      } else {
        setApproveErr(String((e as Error).message ?? e));
      }
    } finally {
      setSelecting(null);
    }
  };

  return (
    <div className="min-h-screen">
      <header className="no-print border-b border-slate-200 bg-white/60 backdrop-blur dark:border-slate-800 dark:bg-slate-900/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-4">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              Caterer — Planning &amp; Quoting
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Turn requirements into three costed menu options.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <HealthBadge />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <div className="no-print grid gap-6 lg:grid-cols-[minmax(0,420px)_1fr]">
          <section>
            <RequirementsForm onSubmit={startPlan} busy={busy} />
          </section>

          <section aria-live="polite" aria-busy={busy}>
            {plan.status === "idle" ? (
              <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-300 p-10 text-center text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <p>Fill in the event requirements to generate costed options.</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                  <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-base font-semibold">
                      {busy ? "Planning…" : restored ? "Restored session" : "Plan run"}
                    </h2>
                    {plan.status !== "streaming" && (
                      <button
                        onClick={clearAll}
                        className="text-xs font-medium text-sky-600 hover:underline dark:text-sky-400"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                  {plan.stages.length > 0 || busy ? (
                    <StageTimeline stages={plan.stages} streaming={busy} />
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      Reopened a previous option set from the link. Pick an option
                      or start a new plan.
                    </p>
                  )}
                </div>

                {plan.status === "error" && (
                  <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-300">
                    Couldn’t complete the plan: {plan.error}
                  </div>
                )}

                {resultErrors.length > 0 && (
                  <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-200">
                    <p className="font-medium">The planner flagged:</p>
                    <ul className="mt-1 list-disc pl-5">
                      {resultErrors.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>

        {/* Full-width option comparison */}
        {plan.status === "done" && options.length > 0 && (
          <section>
            <h2 className="mb-3 text-lg font-semibold">
              Compare {options.length} option{options.length > 1 ? "s" : ""}
            </h2>
            <ConstraintsBanner restrictions={reqs?.dietary_restrictions ?? []} />
            {approveErr && (
              <div role="alert" className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-200">
                {approveErr}
              </div>
            )}
            <OptionsGrid options={options} onSelect={choose} selectingTier={selecting} />
          </section>
        )}

        {order && (
          <>
            <ApprovedOrderPanel order={order} />
            <VendorGate orderId={order.order_id} />
          </>
        )}
      </main>
    </div>
  );
}
