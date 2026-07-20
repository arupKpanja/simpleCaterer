import { afterEach, describe, expect, it, vi } from "vitest";
import { planStream } from "./api";
import type { PlanEvent } from "./types";

function sseStream(chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(enc.encode(c));
      controller.close();
    },
  });
}

describe("planStream (SSE parsing)", () => {
  afterEach(() => vi.restoreAllMocks());

  it("parses data frames into events and returns the final result", async () => {
    const chunks = [
      'data: {"type":"stage","node":"supervisor","stage":"supervisor","message":"go"}\n\n',
      // a single frame split across two chunks exercises the buffer
      'data: {"type":"stage","node":"plan_tier","stage":"tier:essen',
      'tial","message":"m"}\n\n',
      'data: {"type":"result","session_id":"s1","event_id":"e1","options":[],"errors":[],"log":[]}\n\n',
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, body: sseStream(chunks) }),
    );

    const events: PlanEvent[] = [];
    const result = await planStream(
      { event_type: "x", guest_count: 1, budget: 0, dietary_restrictions: [] },
      (ev) => events.push(ev),
    );

    expect(events.map((e) => (e.type === "stage" ? e.stage : e.type))).toEqual([
      "supervisor",
      "tier:essential",
      "result",
    ]);
    expect(result?.event_id).toBe("e1");
    expect(result?.session_id).toBe("s1");
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500, statusText: "err" }));
    await expect(
      planStream(
        { event_type: "x", guest_count: 1, budget: 0, dietary_restrictions: [] },
        () => {},
      ),
    ).rejects.toThrow();
  });
});
