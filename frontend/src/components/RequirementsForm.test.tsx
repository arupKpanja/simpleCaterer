import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import RequirementsForm from "./RequirementsForm";

describe("RequirementsForm", () => {
  it("blocks submit and shows an error when guest count is missing", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<RequirementsForm onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: /generate options/i }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText(/guest count greater than 0/i)).toBeInTheDocument();
  });

  it("produces the /api/plan payload from valid input + a diet chip", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<RequirementsForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText(/event type/i), "gala dinner");
    await user.type(screen.getByLabelText(/guest count/i), "50");
    await user.click(screen.getByRole("button", { name: /^vegetarian$/i }));
    await user.click(screen.getByRole("button", { name: /generate options/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        event_type: "gala dinner",
        guest_count: 50,
        dietary_restrictions: ["vegetarian"],
      }),
    );
  });
});
