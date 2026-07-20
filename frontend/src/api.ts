// Typed client for the Part 1 backend.
//
// Base URL comes from VITE_API_BASE (default http://localhost:8000; the Docker
// stack maps the API to http://localhost:8080). CORS is open on the backend.

import type {
  ApprovedOrder,
  Health,
  PlanEvent,
  PlanResult,
  Requirements,
  StoredEvent,
  VendorOrder,
} from "./types";

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${detail ? `: ${detail}` : ""}`);
  }
  return (await res.json()) as T;
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API_BASE}/health`);
  return jsonOrThrow<Health>(res);
}

/** Re-fetch a persisted option set (options keep their ids, so they stay approvable). */
export async function getOptions(eventId: string): Promise<StoredEvent> {
  return jsonOrThrow<StoredEvent>(await fetch(`${API_BASE}/api/options/${eventId}`));
}

/** Thrown when the event already has a frozen approved order (HTTP 409). */
export class AlreadyApprovedError extends Error {
  constructor(public orderId: string) {
    super("This event already has an approved order.");
    this.name = "AlreadyApprovedError";
  }
}

/** Freeze the chosen option into an approved order. */
export async function approveOrder(
  eventId: string,
  optionId: string,
): Promise<ApprovedOrder> {
  const res = await fetch(`${API_BASE}/api/orders/approve`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ event_id: eventId, option_id: optionId }),
  });
  if (res.status === 409) {
    const body = await res.json().catch(() => null);
    const orderId = body?.detail?.order_id;
    if (orderId) throw new AlreadyApprovedError(orderId);
  }
  return jsonOrThrow<ApprovedOrder>(res);
}

export async function getOrder(orderId: string): Promise<ApprovedOrder> {
  return jsonOrThrow<ApprovedOrder>(await fetch(`${API_BASE}/api/orders/${orderId}`));
}

// --- Vendor approval gate --------------------------------------------------

/** Draft a supplier order; pauses at the approval gate. */
export async function draftVendorOrder(orderId: string): Promise<VendorOrder> {
  return jsonOrThrow<VendorOrder>(
    await fetch(`${API_BASE}/api/orders/${orderId}/vendor-draft`, { method: "POST" }),
  );
}

/** Approve (place) or reject the drafted vendor order. */
export async function decideVendorOrder(
  orderId: string,
  decision: "approve" | "reject",
): Promise<VendorOrder> {
  return jsonOrThrow<VendorOrder>(
    await fetch(`${API_BASE}/api/orders/${orderId}/vendor-decision`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ decision }),
    }),
  );
}

/** Current vendor order for an approved order, or null if none drafted yet. */
export async function getVendorOrder(orderId: string): Promise<VendorOrder | null> {
  const res = await fetch(`${API_BASE}/api/orders/${orderId}/vendor`);
  if (res.status === 404) return null;
  return jsonOrThrow<VendorOrder>(res);
}

/** One-shot plan (no streaming). */
export async function planOnce(reqs: Requirements): Promise<PlanResult> {
  const res = await fetch(`${API_BASE}/api/plan`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(reqs),
  });
  return jsonOrThrow<PlanResult>(res);
}

/**
 * Stream a plan run over SSE, invoking `onEvent` for each stage and the final
 * result. Returns the final PlanResult. Uses fetch streaming (not EventSource)
 * so we can POST a JSON body.
 */
export async function planStream(
  reqs: Requirements,
  onEvent: (ev: PlanEvent) => void,
  signal?: AbortSignal,
): Promise<PlanResult | null> {
  const res = await fetch(`${API_BASE}/api/plan/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(reqs),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`stream failed: ${res.status} ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: PlanResult | null = null;

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      const ev = JSON.parse(payload) as PlanEvent;
      onEvent(ev);
      if (ev.type === "result") result = ev;
    }
  }
  return result;
}
