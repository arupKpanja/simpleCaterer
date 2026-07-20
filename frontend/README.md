# Caterer — Part 1 UI

Frontend for the Planning & Quoting flow (Vite + React + TypeScript + Tailwind).
Talks to the backend in [`../backend/`](../backend/); tasks tracked in
[`../UI_Task.md`](../UI_Task.md).

## Setup

```bash
cd frontend
npm install
cp .env.example .env      # set VITE_API_BASE if the backend isn't on :8000
npm run dev               # http://localhost:5173
```

Point `VITE_API_BASE` at the backend: `http://localhost:8000` (local uvicorn) or
`http://localhost:8080` (the Docker stack). CORS is open on the backend.

## Scripts

- `npm run dev` — dev server with HMR
- `npm run build` — type-check + production build to `dist/`
- `npm run preview` — serve the production build
- `npm test` — Vitest unit/component tests (no backend needed)
- `npm run test:watch` — tests in watch mode
- `npm run e2e` — end-to-end happy path against a **running** backend
  (`API_BASE=http://localhost:8080 npm run e2e`)

## What it does

The full Part 1 flow, end to end:

1. **Requirements form** — event, guests, budget, cuisine, date, location, and
   dietary chips; validated client-side.
2. **Streamed planning** — `POST /api/plan/stream` (SSE) with a live agent-stage
   timeline (`supervisor → tier:* → assemble`).
3. **Compare 3 options** — essential / standard / premium cards: theme, courses
   with allergen pills, decor + venue, cost breakdown, per-guest, budget flag,
   allergen-safe badge, expandable shopping list.
4. **Freeze an order** — "Choose this option" → `POST /api/orders/approve`
   (handles the already-approved case).
5. **Vendor approval gate** — draft the supplier order → review line items →
   approve/reject → placed order with an exportable (CSV/print) shopping list and
   per-item stock impact.
6. **Resume** — `?event&session&order` in the URL restores the whole session on
   reload.

Light/dark theme toggle, responsive layout, and a11y (live regions, alerts,
labelled controls) throughout.

## Layout

| Area | Where |
|---|---|
| API client + types | [`src/api.ts`](src/api.ts), [`src/types.ts`](src/types.ts) |
| Streaming hook | [`src/hooks/usePlan.ts`](src/hooks/usePlan.ts) |
| Components | [`src/components/`](src/components/) — form, timeline, cards, approved-order, vendor gate, health badge, theme toggle |
| Utils | [`src/lib/`](src/lib/) — currency/qty, CSV export |
| Tests | co-located `*.test.ts(x)`; e2e in [`scripts/e2e.mjs`](scripts/e2e.mjs) |
