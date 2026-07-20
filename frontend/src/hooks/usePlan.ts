import { useCallback, useRef, useState } from "react";
import { planStream } from "../api";
import type { PlanResult, Requirements, StageEvent } from "../types";

export type PlanStatus = "idle" | "streaming" | "done" | "error";

export interface PlanState {
  status: PlanStatus;
  stages: StageEvent[];
  result: PlanResult | null;
  error: string | null;
}

const INITIAL: PlanState = { status: "idle", stages: [], result: null, error: null };

/** Drives a streamed /api/plan/stream run and exposes its live state. */
export function usePlan() {
  const [state, setState] = useState<PlanState>(INITIAL);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async (reqs: Requirements) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setState({ status: "streaming", stages: [], result: null, error: null });

    try {
      const result = await planStream(
        reqs,
        (ev) => {
          if (ev.type === "stage") {
            setState((s) => ({ ...s, stages: [...s.stages, ev] }));
          } else {
            setState((s) => ({ ...s, result: ev }));
          }
        },
        ctrl.signal,
      );
      setState((s) => ({ ...s, status: "done", result: result ?? s.result }));
    } catch (e) {
      if (ctrl.signal.aborted) return;
      setState((s) => ({ ...s, status: "error", error: String((e as Error)?.message ?? e) }));
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState(INITIAL);
  }, []);

  /** Inject a completed result (e.g. restored from a URL/session). */
  const hydrate = useCallback((result: PlanResult) => {
    abortRef.current?.abort();
    setState({ status: "done", stages: [], result, error: null });
  }, []);

  return { ...state, run, reset, hydrate };
}
