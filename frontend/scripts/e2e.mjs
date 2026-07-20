// End-to-end happy path against a running backend:
//   plan -> approve -> vendor draft -> vendor place.
// Usage: API_BASE=http://localhost:8080 node scripts/e2e.mjs
// Exits non-zero on any failed assertion.

const BASE = (process.env.API_BASE || "http://localhost:8000").replace(/\/$/, "");

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL:", msg);
    process.exit(1);
  }
  console.log("ok  -", msg);
}

async function json(res) {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

try {
  const health = await json(await fetch(`${BASE}/health`));
  assert(health.status === "ok", `health ok (llm: ${health.llm})`);

  const plan = await json(
    await fetch(`${BASE}/api/plan`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        event_type: "e2e reception",
        guest_count: 100,
        budget: 300000,
        dietary_restrictions: ["vegetarian", "no nuts"],
        cuisine_pref: "Indian",
      }),
    }),
  );
  assert(plan.options.length === 3, "plan returns 3 tiers");
  assert(plan.options.every((o) => o.id), "options carry ids");
  assert(plan.options.every((o) => o.allergen_safe), "all options allergen-safe");

  const std = plan.options.find((o) => o.tier === "standard");
  const order = await json(
    await fetch(`${BASE}/api/orders/approve`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ event_id: plan.event_id, option_id: std.id }),
    }),
  );
  assert(order.order_id && order.snapshot.courses.length > 0, "option frozen into approved order");

  const draft = await json(
    await fetch(`${BASE}/api/orders/${order.order_id}/vendor-draft`, { method: "POST" }),
  );
  assert(draft.status === "awaiting_approval" && draft.lines.length > 0, "vendor order drafted (paused at gate)");

  const placed = await json(
    await fetch(`${BASE}/api/orders/${order.order_id}/vendor-decision`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ decision: "approve" }),
    }),
  );
  assert(placed.status === "placed", "vendor order placed");
  assert(placed.shopping_list.length > 0, "exportable shopping list present");
  assert(placed.stock_impact.length > 0, "stock impact recorded");

  console.log("\nE2E PASS");
} catch (e) {
  console.error("\nE2E ERROR:", e.message);
  console.error(`(is the backend running at ${BASE}?)`);
  process.exit(1);
}
