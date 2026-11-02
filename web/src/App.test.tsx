import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import App, { parseAuditData } from "./App";
import type { AuditData } from "./types";

afterEach(cleanup);

const base: AuditData = {
  generated_at: "2026-11-02T10:00:00Z",
  totals: { info: 1, warning: 2, error: 3 },
  files: [
    {
      path: "data/orders.csv",
      rows: 120,
      columns: { id: "BIGINT", name: "VARCHAR" },
      findings: [
        { check: "nulls", severity: "error", column: "id", message: "has nulls", count: 3, examples: ["a", "b"] },
        { check: "dupes", severity: "warning", column: null, message: "duplicate rows", count: 2, examples: [] },
        { check: "types", severity: "info", column: "name", message: "mixed", count: 1, examples: ["x"] },
      ],
    },
  ],
};

describe("App", () => {
  it("renders title, file name, rows and columns", () => {
    render(<App data={base} />);
    expect(screen.getByRole("heading", { name: "Data audit" })).toBeInTheDocument();
    expect(screen.getByText("data/orders.csv")).toBeInTheDocument();
    expect(screen.getByText(/120 rows/)).toBeInTheDocument();
    expect(screen.getByText(/2 columns/)).toBeInTheDocument();
    expect(screen.getByText(/2026-11-02T10:00:00Z/)).toBeInTheDocument();
  });

  it("shows totals per severity with label and symbol", () => {
    render(<App data={base} />);
    const header = screen.getByTestId("totals");
    expect(header).toHaveTextContent("✖ error 3");
    expect(header).toHaveTextContent("▲ warning 2");
    expect(header).toHaveTextContent("ℹ info 1");
  });

  it("shows extra total keys sorted after the known ones", () => {
    render(<App data={{ ...base, totals: { info: 0, warning: 0, error: 0, zeta: 2, alpha: 1 } }} />);
    const text = screen.getByTestId("totals").textContent ?? "";
    expect(text.indexOf("info")).toBeLessThan(text.indexOf("alpha"));
    expect(text.indexOf("alpha")).toBeLessThan(text.indexOf("zeta"));
    expect(text).toContain("• alpha 1");
  });

  it("renders hostile strings as text only", () => {
    const hostile: AuditData = {
      generated_at: "<b>now</b>",
      totals: { info: 0, warning: 0, error: 0, "<b>sev": 1 },
      files: [
        {
          path: "<script>alert(1)</script>.csv",
          rows: 1,
          columns: { "<script>alert(1)</script>": "VARCHAR" },
          findings: [
            {
              check: "<b>chk",
              severity: "<b>sev",
              column: "<script>alert(1)</script>",
              message: '"><img src=x onerror=alert(1)>',
              count: 1,
              examples: ['"><img src=x onerror=alert(1)>'],
            },
          ],
        },
      ],
    };
    const { container } = render(<App data={hostile} />);
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
    expect(screen.getAllByText('"><img src=x onerror=alert(1)>').length).toBe(2);
    expect(screen.getByText("<b>chk")).toBeInTheDocument();
    expect(screen.getAllByText(/<b>sev/).length).toBeGreaterThan(0);
  });

  it("shows No files audited for empty data", () => {
    render(<App data={{ generated_at: "x", files: [], totals: { info: 0, warning: 0, error: 0 } }} />);
    expect(screen.getByText("No files audited")).toBeInTheDocument();
  });

  it("shows No files audited when data is null", () => {
    render(<App data={null} />);
    expect(screen.getByText("No files audited")).toBeInTheDocument();
  });

  it("shows No problems found for a clean file", () => {
    render(
      <App
        data={{
          generated_at: "x",
          totals: { info: 0, warning: 0, error: 0 },
          files: [{ path: "ok.csv", rows: 1, columns: { a: "INT" }, findings: [] }],
        }}
      />,
    );
    expect(screen.getByText("No problems found")).toBeInTheDocument();
  });

  it("renders unknown severity with fallback symbol and a whitelisted class", () => {
    const data: AuditData = {
      ...base,
      files: [
        {
          ...base.files[0],
          findings: [{ check: "c", severity: "weird sev", column: null, message: "m", count: 1, examples: [] }],
        },
      ],
    };
    const { container } = render(<App data={data} />);
    const cell = container.querySelector("td .sev");
    expect(cell?.textContent).toBe("• weird sev");
    const classes = Array.from(container.querySelectorAll("[class]")).flatMap((e) => Array.from(e.classList));
    expect(classes.some((c) => c.includes("weird"))).toBe(false);
    expect(container.querySelector(".sev-unknown")).not.toBeNull();
  });
});

describe("parseAuditData", () => {
  it("returns null for placeholder, empty and garbage", () => {
    expect(parseAuditData("__AUDIT_DATA__")).toBeNull();
    expect(parseAuditData("  __AUDIT_DATA__\n")).toBeNull();
    expect(parseAuditData("")).toBeNull();
    expect(parseAuditData(null)).toBeNull();
    expect(parseAuditData("{not json")).toBeNull();
    expect(parseAuditData("42")).toBeNull();
    expect(parseAuditData('{"files": 3}')).toBeNull();
  });
  it("parses valid data", () => {
    expect(parseAuditData(JSON.stringify(base))?.files).toHaveLength(1);
  });
});
