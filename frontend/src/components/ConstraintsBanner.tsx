function pretty(r: string): string {
  return r.charAt(0).toUpperCase() + r.slice(1);
}

export default function ConstraintsBanner({ restrictions }: { restrictions: string[] }) {
  const has = restrictions.length > 0;
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/60 px-3 py-2 text-sm dark:border-emerald-900 dark:bg-emerald-950/30">
      <span className="font-medium text-emerald-800 dark:text-emerald-300">
        All options honour:
      </span>
      {has ? (
        restrictions.map((r) => (
          <span
            key={r}
            className="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-emerald-700 shadow-sm dark:bg-emerald-900/40 dark:text-emerald-200"
          >
            {pretty(r)}
          </span>
        ))
      ) : (
        <span className="text-emerald-700 dark:text-emerald-300">no dietary restrictions</span>
      )}
      <span className="text-emerald-700/80 dark:text-emerald-300/80">
        · allergen &amp; budget checks enforced server-side
      </span>
    </div>
  );
}
