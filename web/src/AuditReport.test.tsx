import { render, screen, cleanup, waitFor, fireEvent, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import AuditReport, { parseAuditData } from "./AuditReport";
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

describe("AuditReport", () => {
  it("renders title, file name, rows and columns", () => {
    render(<AuditReport data={base} />);
    expect(screen.getByRole("heading", { name: "Data audit" })).toBeInTheDocument();
    expect(screen.getByText("data/orders.csv")).toBeInTheDocument();
    expect(screen.getByText(/120 rows/)).toBeInTheDocument();
    expect(screen.getByText(/2 columns/)).toBeInTheDocument();
    expect(screen.getByText(/2026-11-02T10:00:00Z/)).toBeInTheDocument();
  });

  it("shows totals per severity with label and symbol", async () => {
    render(<AuditReport data={base} />);
    const header = screen.getByTestId("totals");
    await waitFor(() => expect(header).toHaveTextContent("✖ error 3"));
    expect(header).toHaveTextContent("▲ warning 2");
    expect(header).toHaveTextContent("ℹ info 1");
  });

  it("shows extra total keys sorted after the known ones", async () => {
    render(<AuditReport data={{ ...base, totals: { info: 0, warning: 0, error: 0, zeta: 2, alpha: 1 } }} />);
    await waitFor(() => expect(screen.getByTestId("totals")).toHaveTextContent("• alpha 1"));
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
    const { container } = render(<AuditReport data={hostile} />);
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
    expect(screen.getAllByText('"><img src=x onerror=alert(1)>').length).toBe(2);
    expect(screen.getByText("<b>chk")).toBeInTheDocument();
    expect(screen.getAllByText(/<b>sev/).length).toBeGreaterThan(0);
  });

  it("shows No files audited for empty data", () => {
    render(<AuditReport data={{ generated_at: "x", files: [], totals: { info: 0, warning: 0, error: 0 } }} />);
    expect(screen.getByText("No files audited")).toBeInTheDocument();
  });

  it("shows No files audited when data is null", () => {
    render(<AuditReport data={null} />);
    expect(screen.getByText("No files audited")).toBeInTheDocument();
  });

  it("shows No problems found for a clean file", () => {
    render(
      <AuditReport
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
    const { container } = render(<AuditReport data={data} />);
    const cell = container.querySelector("td .sev");
    expect(cell?.textContent).toBe("• weird sev");
    const classes = Array.from(container.querySelectorAll("[class]")).flatMap((e) => Array.from(e.classList));
    expect(classes.some((c) => c.includes("weird"))).toBe(false);
    expect(container.querySelector(".sev-unknown")).not.toBeNull();
  });
});

function withExamples(examples: string[]): AuditData {
  return {
    generated_at: "x",
    totals: { info: 0, warning: 0, error: 1 },
    files: [
      {
        path: "e.csv",
        rows: 1,
        columns: { a: "INT" },
        findings: [{ check: "c", severity: "error", column: "a", message: "m", count: examples.length, examples }],
      },
    ],
  };
}

describe("example list toggle", () => {
  it("shows 3 of 5 examples and expands on click", () => {
    const { container } = render(<AuditReport data={withExamples(["e1", "e2", "e3", "e4", "e5"])} />);
    expect(container.querySelectorAll("code.example")).toHaveLength(3);
    const toggle = screen.getByRole("button", { name: /show all 5/i });
    expect(toggle.tagName).toBe("BUTTON");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(container.querySelectorAll("code.example")).toHaveLength(5);
    expect(screen.getByText("e5")).toBeInTheDocument();
  });

  it("has no toggle for 3 or fewer examples", () => {
    render(<AuditReport data={withExamples(["e1", "e2", "e3"])} />);
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByText("e3")).toBeInTheDocument();
  });
});

describe("count-up", () => {
  it("ends on the exact totals", async () => {
    render(<AuditReport data={{ ...withExamples([]), totals: { info: 7, warning: 1234, error: 0 } }} />);
    const totals = screen.getByTestId("totals");
    await waitFor(() => expect(totals).toHaveTextContent("▲ warning 1234"));
    expect(totals).toHaveTextContent("ℹ info 7");
    expect(totals).toHaveTextContent("✖ error 0");
  });
});

describe("hostile data in the animated components", () => {
  it("renders every field as text and creates no elements", async () => {
    const evil = '"><img src=x onerror=alert(1)>';
    const data: AuditData = {
      generated_at: "<b>now</b>",
      totals: { error: 1, "<script>sev</script>": 2 },
      files: [
        {
          path: "<script>alert(1)</script>.csv",
          rows: 1,
          columns: { "<b>col": "VARCHAR" },
          findings: [
            {
              check: "<script>chk</script>",
              severity: "<img src=x>",
              column: "<b>col",
              message: evil,
              count: 1,
              examples: [evil, "<b>2", "<script>3</script>", "<img src=4>", "<b>5"],
            },
          ],
        },
      ],
    };
    const { container } = render(<AuditReport data={data} />);
    fireEvent.click(screen.getByRole("button", { name: /show all 5/i }));
    await waitFor(() => expect(screen.getByTestId("totals")).toHaveTextContent("sev</script> 2"));
    for (const tag of ["script", "img", "b"]) expect(container.querySelector(tag)).toBeNull();
    expect(screen.getByText("<script>chk</script>")).toBeInTheDocument();
    expect(screen.getByText("<img src=4>")).toBeInTheDocument();
    expect(screen.getAllByText(evil).length).toBe(2);
    const classes = Array.from(container.querySelectorAll("[class]")).flatMap((e) => Array.from(e.classList));
    expect(classes.some((c) => c.includes("<") || c.includes("sev</"))).toBe(false);
  });
});

function withProfile(extra: Partial<AuditData["files"][0]>): AuditData {
  return { ...base, files: [{ ...base.files[0], ...extra }] };
}

describe("quality badge", () => {
  it("shows the score and uses outline at 50 or above", () => {
    render(<AuditReport data={withProfile({ score: 72 })} />);
    const badge = screen.getByTestId("quality");
    expect(badge).toHaveTextContent("Quality 72/100");
    expect(badge).toHaveAttribute("data-variant", "outline");
  });

  it("uses the destructive variant under 50", () => {
    render(<AuditReport data={withProfile({ score: 49 })} />);
    expect(screen.getByTestId("quality")).toHaveAttribute("data-variant", "destructive");
  });

  it("renders no badge when the score is absent", () => {
    render(<AuditReport data={base} />);
    expect(screen.queryByTestId("quality")).toBeNull();
    expect(screen.queryByText(/Quality/)).toBeNull();
  });
});

describe("column profile", () => {
  const profile = {
    id: { type: "BIGINT", missing: 0, distinct: 5, min: 1, max: 9, mean: 4.5 },
    name: { type: "VARCHAR", missing: 2, distinct: 3 },
    "<script>x</script>": { type: "DATE", missing: 0, distinct: 1, min: "2024-01-01", max: null },
  };

  it("is collapsed by default and expands on click", () => {
    render(<AuditReport data={withProfile({ profile })} />);
    expect(screen.queryByRole("columnheader", { name: "Distinct" })).toBeNull();
    const toggle = screen.getByRole("button", { name: "Column profile" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const table = screen.getByText("Distinct").closest("table") as HTMLElement;
    for (const h of ["Column", "Type", "Missing", "Distinct", "Min", "Max", "Mean"]) {
      expect(within(table).getByRole("columnheader", { name: h })).toBeInTheDocument();
    }
    expect(screen.getByText("4.5")).toBeInTheDocument();
  });

  it("shows a dash for absent statistics", () => {
    render(<AuditReport data={withProfile({ profile: { name: profile.name } })} />);
    fireEvent.click(screen.getByRole("button", { name: "Column profile" }));
    const row = screen.getByText("VARCHAR").closest("tr") as HTMLElement;
    expect(row.textContent?.match(/—/g)).toHaveLength(3);
  });

  it("renders a column name with markup as text", () => {
    const { container } = render(<AuditReport data={withProfile({ profile })} />);
    fireEvent.click(screen.getByRole("button", { name: "Column profile" }));
    expect(screen.getByText("<script>x</script>")).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
  });

  it("is absent for old data without a profile", () => {
    render(<AuditReport data={base} />);
    expect(screen.queryByRole("button", { name: "Column profile" })).toBeNull();
  });
});

describe("parseAuditData", () => {
  it("returns null for empty and garbage", () => {
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
