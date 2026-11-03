import { useRef, useState, type DragEvent } from "react";
import { Button } from "@/components/ui/button";
import AuditReport, { parseAuditData } from "./AuditReport";
import type { AuditData } from "./types";

export const MAX_BYTES = 50 * 1024 * 1024;
const ACCEPTED = [".csv", ".parquet"];

type State =
  | { phase: "idle"; error?: string }
  | { phase: "uploading"; name: string }
  | { phase: "done"; data: AuditData };

function problemWith(file: File): string | null {
  const lower = file.name.toLowerCase();
  if (!ACCEPTED.some((ext) => lower.endsWith(ext))) return "Choose a .csv or .parquet file.";
  if (file.size > MAX_BYTES) return `That file is larger than ${MAX_BYTES / (1024 * 1024)} MB.`;
  return null;
}

async function failureMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  } catch {
    // fall through to the generic message
  }
  return `The audit failed (HTTP ${response.status}).`;
}

export default function App() {
  const [state, setState] = useState<State>({ phase: "idle" });
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function audit(file: File) {
    const problem = problemWith(file);
    if (problem) {
      setState({ phase: "idle", error: problem });
      return;
    }
    setState({ phase: "uploading", name: file.name });
    try {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch("/api/audit", { method: "POST", body: form });
      if (!response.ok) {
        setState({ phase: "idle", error: await failureMessage(response) });
        return;
      }
      const data = parseAuditData(await response.text());
      setState(data ? { phase: "done", data } : { phase: "idle", error: "The server sent a result this page cannot read." });
    } catch {
      setState({ phase: "idle", error: "Could not reach the audit server." });
    }
  }

  function pick(files: FileList | null) {
    const file = files?.[0];
    if (file) void audit(file);
    if (input.current) input.current.value = "";
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    pick(event.dataTransfer.files);
  }

  if (state.phase === "done") {
    return (
      <>
        <div className="mx-auto max-w-6xl px-4 pt-4">
          <Button variant="outline" onClick={() => setState({ phase: "idle" })}>
            Audit another file
          </Button>
        </div>
        <AuditReport data={state.data} />
      </>
    );
  }

  const busy = state.phase === "uploading";
  return (
    <main className="mx-auto max-w-2xl p-4">
      <h1 className="text-2xl font-semibold">Data audit</h1>
      <p className="mb-4 text-muted-foreground">
        Upload a CSV or Parquet file to check it for missing values, duplicates, mixed types and outliers.
      </p>
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed p-10 text-center transition-colors focus-within:ring-3 focus-within:ring-ring/50 ${
          dragging ? "border-primary bg-muted" : "border-border"
        }`}
      >
        <span className="font-medium">{busy ? `Auditing ${state.name}…` : "Drop a file here, or choose one"}</span>
        <span className="text-sm text-muted-foreground">.csv or .parquet, up to {MAX_BYTES / (1024 * 1024)} MB</span>
        <input
          ref={input}
          type="file"
          accept={ACCEPTED.join(",")}
          className="sr-only"
          disabled={busy}
          onChange={(e) => pick(e.target.files)}
          aria-label="Audit a file"
        />
        <span className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground">
          Choose file
        </span>
      </label>
      {state.phase === "idle" && state.error && (
        <p role="alert" className="mt-4 text-destructive">
          {state.error}
        </p>
      )}
    </main>
  );
}
