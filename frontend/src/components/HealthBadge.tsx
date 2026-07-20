import { useEffect, useState } from "react";
import { API_BASE, getHealth } from "../api";
import type { Health } from "../types";

type State =
  | { kind: "loading" }
  | { kind: "ok"; health: Health }
  | { kind: "error"; message: string };

export default function HealthBadge() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let alive = true;
    getHealth()
      .then((health) => alive && setState({ kind: "ok", health }))
      .catch((e) => alive && setState({ kind: "error", message: String(e.message ?? e) }));
    return () => {
      alive = false;
    };
  }, []);

  const dot = (color: string) => (
    <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />
  );

  let content: JSX.Element;
  if (state.kind === "loading") {
    content = (
      <>
        {dot("bg-slate-400 animate-pulse")}
        <span>Connecting to backend…</span>
      </>
    );
  } else if (state.kind === "error") {
    content = (
      <>
        {dot("bg-rose-500")}
        <span>Backend offline — {API_BASE}</span>
      </>
    );
  } else {
    const usingLlm = state.health.llm === "ollama";
    content = (
      <>
        {dot("bg-emerald-500")}
        <span>Backend online</span>
        <span className="opacity-40">·</span>
        <span className="inline-flex items-center gap-1">
          {dot(usingLlm ? "bg-emerald-500" : "bg-amber-500")}
          LLM: {usingLlm ? "Ollama" : "deterministic fallback"}
        </span>
      </>
    );
  }

  return (
    <div
      className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-1.5 text-sm text-slate-600 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-300"
      title={API_BASE}
    >
      {content}
    </div>
  );
}
