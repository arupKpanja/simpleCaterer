# Part 1 UI — Task Tracker

Frontend for **Part 1 (Planning & Quoting)**: turn a live requirements form into
three streamed, comparable costed menu options, let the owner freeze one, and run
the vendor approval gate — all against the existing backend.

See the plan ([`caterer-multi-agent-langgraph-plan.md`](caterer-multi-agent-langgraph-plan.md))
and the static mockup ([`caterer-mockups.html`](caterer-mockups.html)) for the
intended look. Backend lives in [`backend/`](backend/) and is complete.

Status legend: ⬜ not started · 🟡 in progress · ✅ done

---

## Backend the UI builds on (already live)

| UI action | Endpoint |
|---|---|
| Submit requirements, stream stages + options | `POST /api/plan/stream` (SSE) — or `POST /api/plan` (one-shot) |
| Re-fetch a persisted option set | `GET /api/options/{event_id}` |
| Freeze the chosen tier | `POST /api/orders/approve` `{event_id, option_id}` |
| Read a frozen order | `GET /api/orders/{order_id}` |
| Draft supplier order (pauses at gate) | `POST /api/orders/{order_id}/vendor-draft` |
| Approve/reject the draft | `POST /api/orders/{order_id}/vendor-decision` `{decision}` |
| Read vendor order (draft/placed/rejected) | `GET /api/orders/{order_id}/vendor` |
| Resume/inspect a session | `GET /api/sessions/{session_id}/state` |
| LLM/health status | `GET /health` |

SSE stage events stream as `supervisor → tier:essential / tier:standard /
tier:premium → assemble → result`; the `result` event carries `event_id`,
`session_id`, and the sorted `options` array.

Each option contains: `id`, `tier`, `theme`, `courses[]` (course, dish,
diet_tags, allergens, serving_cost), `decor`, `venue`, `food_cost`, `decor_cost`,
`venue_cost`, `total_cost`, `per_guest`, `within_budget`, `overage`,
`allergen_safe`, `shopping_list[]`.

---

## Tech stack

- **Next.js (React) + Tailwind** per the plan (chat-style planning UI + option
  cards). A single-page React app is acceptable if simpler.
- Talks to the API base URL from an env var (`NEXT_PUBLIC_API_BASE`, default
  `http://localhost:8000`; the Docker stack maps `8080`). CORS is already open on
  the backend.

---

## U1 — Scaffold + API client ✅
Frontend app + typed API layer are up.
- **Delivered:** `frontend/` = **Vite + React + TS + Tailwind** (SPA, per the
  allowed alternative to Next.js). Typed client `src/api.ts` (`getHealth`,
  `planOnce`, SSE `planStream`) + `src/types.ts`; env-driven base URL
  (`VITE_API_BASE`, default `:8000`, `.env` set to the Docker stack `:8080`);
  app shell with a live backend/LLM `HealthBadge` reading `GET /health`.
- **Verified:** `npm run build` type-checks + bundles; `npm run dev` serves the
  app on http://localhost:5173.

## U2 — Requirements form ✅
- **Delivered:** `src/components/RequirementsForm.tsx` — event type, guest count,
  budget, cuisine (select), date, location, and dietary-restriction **chips**
  (vegetarian / vegan / gluten-free / no nuts / no dairy / no shellfish, mapped to
  the phrases the backend parser understands); client-side validation
  (event_type required, guest_count > 0, budget ≥ 0) with inline errors and a
  disabled submit; a "Fill sample" shortcut. Wired into `App.tsx`, which shows the
  produced `/api/plan` payload (U3 will stream it).
- **Verified:** `npm run build` type-checks + bundles; dev server serves it.

## U3 — Streaming plan run (SSE) ✅
- **Delivered:** `src/hooks/usePlan.ts` (drives `/api/plan/stream` with abort;
  tracks status/stages/result/error), `src/components/StageTimeline.tsx` (live
  stages with spinner on the in-flight one, ticks on done), wired into `App.tsx`
  with a busy form, a live timeline, network-error + backend-error (invalid reqs)
  states, and a compact result summary (full cards land in U4).
- **Verified:** build passes; backend SSE frames confirmed as `data:{json}\n\n`
  in the exact `supervisor → tier:* → assemble → result` sequence the parser +
  timeline consume (with real LLM themes).
- **Depends on:** U2.

## U4 — Option comparison cards ✅
- **Delivered:** `src/components/OptionCard.tsx` — per-tier accent, theme, courses
  with allergen pills, decor + venue + food breakdown, big total + per-guest, a
  within-budget/over-by flag, an allergen-safe/allergen-risk badge, and an
  expandable shopping list (with short-by markers). `src/components/OptionsGrid.tsx`
  lays them 3-up (stacks on mobile) and marks the **standard** tier "Recommended".
  `src/lib/format.ts` for currency/qty. App restructured so the cards span full
  width below the form + timeline. The card exposes an optional `onSelect` (wired
  in U5).
- **Verified:** build passes (39 modules); dev server serves it.
- **Depends on:** U3.

## U5 — Select + freeze approved order ✅
- **Delivered:** `api.ts` `approveOrder` (POST `/api/orders/approve`, throws
  `AlreadyApprovedError` with the existing `order_id` on 409) + `getOrder`;
  `ApprovedOrder` type; `src/components/ApprovedOrderPanel.tsx` (frozen order meta
  + the snapshot menu via `OptionCard`); App `choose()` wires each card's
  "Choose this option" → freeze, resets on a new plan, and on 409 fetches +
  shows the already-approved order.
- **Verified:** build passes; live contract confirmed — approve → 201 with
  snapshot, second approve → 409 with `detail.order_id`, `GET /api/orders/{id}` →
  200.
- **Depends on:** U4. (URL persistence of ids lands in U7.)

## U6 — Vendor approval gate ✅
- **Delivered:** `api.ts` `draftVendorOrder` / `decideVendorOrder` /
  `getVendorOrder` (+ `VendorOrder`/`StockImpactLine` types);
  `src/components/VendorGate.tsx` — restores any existing vendor order on mount,
  then: idle → "Draft supplier order" → **awaiting** (line-item table + total +
  Approve/Reject) → **placed** (exportable shopping list + per-item stock-impact
  table with short-by flags) or **rejected**. Wired into `App.tsx` below the
  approved order.
- **Verified:** build passes; live flow confirmed — get(none)=404,
  draft="awaiting_approval" (no export yet), approve="placed" with a 10-item
  export list and 10 stock-impact rows.
- **Depends on:** U5.

## U7 — Sessions: resume + history ✅
- **Delivered:** `api.ts` `getOptions(event_id)` (options keep their ids →
  still approvable); `usePlan.hydrate` to inject a restored result; App writes
  `?event&session&order` to the URL (`history.replaceState`) and, on first load,
  restores the option set via `GET /api/options/{event_id}` and the approved order
  via `GET /api/orders/{order_id}` (which also re-hydrates the vendor gate). A
  "Restored session" note replaces the empty timeline.
- **Verified:** build passes; live — `getOptions` returns 3 id-bearing options +
  requirements, `GET /api/sessions/{id}/state` → 200.
- **Done when:** reloading the page restores the last option set + approved order. ✔

## U8 — Polish: responsive, theme, a11y ✅
- **Delivered:** class-based light/dark theme with a no-flash init script +
  `ThemeToggle` (persisted to localStorage); `ConstraintsBanner` summarising the
  active dietary restrictions above the options; CSV **Download** + **Print**
  (with `.no-print` hiding the header/form/timeline) of the placed shopping list
  (`src/lib/export.ts`); a11y — `aria-live`/`aria-busy` on the run region,
  `role="alert"` on error banners, `aria-pressed` chips, labelled controls,
  focus-visible rings; responsive grid (cards stack on mobile); `$` currency
  formatting throughout.
- **Verified:** build passes (45 modules); dev server serves; theme-init present.
- **Done when:** usable and accessible on desktop + mobile in both themes. ✔

## U9 — Tests + README ✅
- **Delivered:** Vitest + Testing Library set up (`vitest.config.ts`,
  `src/test/setup.ts`, tests excluded from the build tsconfig). Tests:
  `api.test.ts` (SSE frame parsing incl. split frames + error path),
  `lib/format.test.ts`, `RequirementsForm.test.tsx` (validation + payload),
  `OptionCard.test.tsx` (render, expandable list, select). `scripts/e2e.mjs`
  runs the happy path (plan → approve → vendor draft → place) against a running
  backend (`npm run e2e`). README refreshed with scripts + flow.
- **Verified:** `npm test` → **9 passed**; `npm run e2e` → **E2E PASS** (against
  the live stack, llm: ollama); `npm run build` clean.

---

### Suggested order
U1 → U2 → U3 → U4 (gets the core planning-to-comparison flow on screen), then
U5 → U6 (order + vendor gate), then U7, U8, U9.

> Part 2 (event-day ops dashboard + staff app) is a separate UI, out of scope here.
