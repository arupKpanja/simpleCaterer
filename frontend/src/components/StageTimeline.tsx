import type { StageEvent } from "../types";

function prettyStage(stage: string): string {
  if (stage === "supervisor") return "Supervisor";
  if (stage === "assemble") return "Assembled options";
  if (stage.startsWith("tier:")) {
    const t = stage.slice(5);
    return `${t.charAt(0).toUpperCase()}${t.slice(1)} tier`;
  }
  return stage;
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin text-sky-500" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

function Check() {
  return (
    <svg className="h-4 w-4 text-emerald-500" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 10.7a1 1 0 111.4-1.4l3.1 3.1 6.8-6.8a1 1 0 011.4 0z" clipRule="evenodd" />
    </svg>
  );
}

export default function StageTimeline({
  stages,
  streaming,
}: {
  stages: StageEvent[];
  streaming: boolean;
}) {
  return (
    <ol className="space-y-3">
      {stages.map((s, i) => {
        const isLast = i === stages.length - 1;
        const inFlight = streaming && isLast;
        return (
          <li key={`${s.stage}-${i}`} className="flex gap-3">
            <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center">
              {inFlight ? <Spinner /> : <Check />}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                {prettyStage(s.stage)}
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-400">{s.message}</p>
            </div>
          </li>
        );
      })}
      {streaming && stages.length === 0 && (
        <li className="flex items-center gap-3 text-sm text-slate-500">
          <Spinner /> Starting…
        </li>
      )}
    </ol>
  );
}
