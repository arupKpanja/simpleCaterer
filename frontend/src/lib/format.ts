export function currency(n: number): string {
  return "₹" + Math.round(n ?? 0).toLocaleString("en-IN");
}

/** Compact quantity, e.g. 14.4 -> "14.4", 15 -> "15". */
export function qty(n: number): string {
  return Number.isInteger(n) ? String(n) : String(Math.round(n * 1000) / 1000);
}
