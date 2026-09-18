import { describe, expect, it } from "vitest";
import { currency, qty } from "./format";

describe("format", () => {
  it("formats currency with the $ symbol and grouping", () => {
    expect(currency(0)).toBe("$0");
    expect(currency(26956.4)).toBe("$26,956");
    expect(currency(119312)).toBe("$119,312"); // en-US grouping
  });

  it("renders quantities compactly", () => {
    expect(qty(15)).toBe("15");
    expect(qty(14.4)).toBe("14.4");
    expect(qty(0)).toBe("0");
  });
});
