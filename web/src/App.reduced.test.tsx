import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import type { AuditData } from "./types";

// Must be set before framer-motion reads the preference (it reads it once).
beforeAll(() => {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }));
});
afterEach(cleanup);

const data: AuditData = {
  generated_at: "2026-11-02T10:00:00Z",
  totals: { info: 0, warning: 2, error: 3 },
  files: [
    {
      path: "data/orders.csv",
      rows: 5,
      columns: { id: "BIGINT" },
      findings: [
        { check: "nulls", severity: "error", column: "id", message: "has nulls", count: 3, examples: ["a", "b", "c", "d", "e"] },
      ],
    },
  ],
};

describe("prefers-reduced-motion", () => {
  it("renders all content at once and the toggle still works", async () => {
    const { default: App } = await import("./App");
    expect(window.matchMedia("(prefers-reduced-motion: reduce)").matches).toBe(true);
    const { container } = render(<App data={data} />);
    expect(screen.getByText("data/orders.csv")).toBeInTheDocument();
    expect(screen.getByText("has nulls")).toBeInTheDocument();
    // count-up is skipped: final totals are present synchronously
    expect(screen.getByTestId("totals")).toHaveTextContent("✖ error 3");
    expect(screen.getByTestId("totals")).toHaveTextContent("▲ warning 2");
    expect(container.querySelectorAll("code.example")).toHaveLength(3);
    const toggle = screen.getByRole("button", { name: /show all 5/i });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(container.querySelectorAll("code.example")).toHaveLength(5);
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});
