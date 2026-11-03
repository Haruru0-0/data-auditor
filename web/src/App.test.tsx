import { render, screen, cleanup, waitFor, fireEvent } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { MAX_BYTES } from "./App";

const result = {
  generated_at: "2026-11-03T10:00:00Z",
  totals: { error: 1, warning: 0, info: 0 },
  files: [
    {
      path: "orders.csv",
      rows: 12,
      columns: { id: "BIGINT" },
      findings: [{ check: "missing", severity: "error", column: "id", message: "all values missing", count: 12, examples: [] }],
    },
  ],
};

const fetchMock = vi.fn();
beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  cleanup();
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

const choose = (file: File) =>
  fireEvent.change(screen.getByLabelText("Audit a file"), { target: { files: [file] } });
const csv = (name = "orders.csv") => new File(["id\n1\n"], name, { type: "text/csv" });

describe("App", () => {
  it("asks for a file first", () => {
    render(<App />);
    expect(screen.getByText(/Drop a file here/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("posts the chosen file to the API and shows the audit", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify(result), { status: 200 }));
    render(<App />);
    choose(csv());
    expect(await screen.findByText("orders.csv")).toBeInTheDocument();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/audit");
    expect(init.method).toBe("POST");
    expect((init.body as FormData).get("file")).toBeInstanceOf(File);
    expect(screen.getByRole("button", { name: "Audit another file" })).toBeInTheDocument();
  });

  it("returns to the upload form for another file", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify(result), { status: 200 }));
    render(<App />);
    choose(csv());
    fireEvent.click(await screen.findByRole("button", { name: "Audit another file" }));
    expect(screen.getByText(/Drop a file here/)).toBeInTheDocument();
  });

  it("shows the server's message when the audit is refused", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: "file is larger than 50 MB" }), { status: 413 }));
    render(<App />);
    choose(csv());
    expect(await screen.findByRole("alert")).toHaveTextContent("file is larger than 50 MB");
  });

  it("explains an unreachable server", async () => {
    fetchMock.mockRejectedValue(new TypeError("network"));
    render(<App />);
    choose(csv());
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reach the audit server");
  });

  it("rejects other file types without calling the server", async () => {
    render(<App />);
    choose(new File(["x"], "notes.txt", { type: "text/plain" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(".csv or .parquet");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects an oversized file without calling the server", async () => {
    render(<App />);
    const big = csv("big.csv");
    Object.defineProperty(big, "size", { value: MAX_BYTES + 1 });
    choose(big);
    expect(await screen.findByRole("alert")).toHaveTextContent("larger than 50 MB");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a reply it cannot read", async () => {
    fetchMock.mockResolvedValue(new Response("not json", { status: 200 }));
    render(<App />);
    choose(csv());
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("cannot read"));
  });

  it("accepts a dropped file", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify(result), { status: 200 }));
    render(<App />);
    fireEvent.drop(screen.getByText(/Drop a file here/), { dataTransfer: { files: [csv()] } });
    expect(await screen.findByText("orders.csv")).toBeInTheDocument();
  });
});
