import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import OptionCard from "./OptionCard";
import type { Option } from "../types";

const OPTION: Option = {
  id: "opt1",
  tier: "standard",
  theme: "Taste of Test",
  courses: [
    { course: "main", dish_id: 1, dish: "Veg Biryani", cuisine: "Indian", diet_tags: ["vegan"], allergens: [], serving_cost: 3 },
    { course: "dessert", dish_id: 2, dish: "Gulab Jamun", cuisine: "Indian", diet_tags: [], allergens: ["dairy", "gluten"], serving_cost: 2 },
  ],
  decor: { name: "Classic Celebration", cost: 18000 },
  venue: { name: "Riverside Marquee", cost: 50000 },
  food_cost: 500,
  decor_cost: 18000,
  venue_cost: 50000,
  total_cost: 68500,
  per_guest: 685,
  within_budget: true,
  overage: 0,
  allergen_safe: true,
  shopping_list: [
    { item: "Basmati rice", unit: "kg", qty: 12, price_per_unit: 120, line_cost: 1440, stock_qty: 200, short_by: 0, allergens: [] },
  ],
};

describe("OptionCard", () => {
  it("renders theme, dishes, allergen pills, and budget flag", () => {
    render(<OptionCard option={OPTION} />);
    expect(screen.getByText("Taste of Test")).toBeInTheDocument();
    expect(screen.getByText("Veg Biryani")).toBeInTheDocument();
    expect(screen.getByText("dairy")).toBeInTheDocument();
    expect(screen.getByText(/within budget/i)).toBeInTheDocument();
    expect(screen.getByText(/allergen-safe/i)).toBeInTheDocument();
  });

  it("expands the shopping list on demand", async () => {
    const user = userEvent.setup();
    render(<OptionCard option={OPTION} />);
    expect(screen.queryByText(/Basmati rice/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /show shopping list/i }));
    expect(screen.getByText(/Basmati rice/)).toBeInTheDocument();
  });

  it("shows the select button only when onSelect is provided", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<OptionCard option={OPTION} onSelect={onSelect} />);
    await user.click(screen.getByRole("button", { name: /choose this option/i }));
    expect(onSelect).toHaveBeenCalledWith(OPTION);
  });
});
