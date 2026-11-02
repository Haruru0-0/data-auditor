import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { AuditData } from "./types";

// Normal (not reduced) motion: matchMedia exists but never matches.
beforeAll(() => {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false,
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
  generated_at: "x",
  totals: { info: 0, warning: 0, error: 40 },
  files: [{ path: "a.csv", rows: 1, columns: { a: "INT" }, findings: [] }],
};

describe("normal motion", () => {
  it("count-up starts below the total and entrance elements are offset", async () => {
    const { container } = render(<App data={data} />);
    const totals = screen.getByTestId("totals");
    expect(totals).toHaveTextContent("✖ error 0");
    const moved = Array.from(container.querySelectorAll<HTMLElement>("[style]")).filter((e) =>
      /translate/.test(e.style.transform),
    );
    expect(moved.length).toBeGreaterThan(0);
    await waitFor(() => expect(totals).toHaveTextContent("✖ error 40"));
  });
});
