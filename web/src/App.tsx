import type { AuditData, FileEntry, Finding } from "./types";

// A regex, not a string constant: the Python side replaces every literal
// placeholder in the file, so the bundle must not contain it.
const PLACEHOLDER = /^__AUDIT_DATA_{2}$/;
const KNOWN = ["error", "warning", "info"] as const;

// Fixed whitelist: class names and symbols never come from the data.
const SEVERITY_STYLE: Record<string, { symbol: string; cls: string }> = {
  error: { symbol: "✖", cls: "sev-error" },
  warning: { symbol: "▲", cls: "sev-warning" },
  info: { symbol: "ℹ", cls: "sev-info" },
};
const FALLBACK_STYLE = { symbol: "•", cls: "sev-unknown" };

function styleFor(severity: string) {
  return Object.hasOwn(SEVERITY_STYLE, severity) ? SEVERITY_STYLE[severity] : FALLBACK_STYLE;
}

export function parseAuditData(text: string | null | undefined): AuditData | null {
  if (text == null) return null;
  const trimmed = text.trim();
  if (trimmed === "" || PLACEHOLDER.test(trimmed)) return null;
  try {
    const value: unknown = JSON.parse(trimmed);
    if (typeof value !== "object" || value === null) return null;
    const obj = value as Partial<AuditData>;
    if (!Array.isArray(obj.files)) return null;
    return {
      generated_at: typeof obj.generated_at === "string" ? obj.generated_at : "",
      files: obj.files,
      totals: obj.totals && typeof obj.totals === "object" ? obj.totals : {},
    };
  } catch {
    return null;
  }
}

function Severity({ severity }: { severity: string }) {
  const { symbol, cls } = styleFor(severity);
  return <span className={`sev ${cls}`}>{`${symbol} ${severity}`}</span>;
}

function Totals({ totals }: { totals: Record<string, number> }) {
  const extra = Object.keys(totals)
    .filter((k) => !(KNOWN as readonly string[]).includes(k))
    .sort();
  const keys = [...KNOWN, ...extra];
  return (
    <p className="totals" data-testid="totals">
      {keys.map((key) => (
        <span className="total" key={key}>
          <Severity severity={key} /> <strong>{String(totals[key] ?? 0)}</strong>
        </span>
      ))}
    </p>
  );
}

function FindingsTable({ findings }: { findings: Finding[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Severity</th>
            <th>Check</th>
            <th>Column</th>
            <th>Message</th>
            <th>Count</th>
            <th>Examples</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((f, i) => (
            <tr key={i}>
              <td>
                <Severity severity={String(f.severity)} />
              </td>
              <td>{f.check}</td>
              <td>{f.column ?? ""}</td>
              <td>{f.message}</td>
              <td className="num">{f.count}</td>
              <td>
                {(f.examples ?? []).map((ex, j) => (
                  <code className="example" key={j}>
                    {ex}
                  </code>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FileCard({ file }: { file: FileEntry }) {
  const columnCount = Object.keys(file.columns ?? {}).length;
  const findings = file.findings ?? [];
  return (
    <section className="card">
      <h2 className="path">{file.path}</h2>
      <p className="meta">
        {file.rows} rows, {columnCount} columns
      </p>
      {findings.length === 0 ? <p className="clean">No problems found</p> : <FindingsTable findings={findings} />}
    </section>
  );
}

export default function App({ data }: { data: AuditData | null }) {
  const files = data?.files ?? [];
  return (
    <main>
      <header>
        <h1>Data audit</h1>
        {data && files.length > 0 && (
          <>
            <p className="generated">Generated at {data.generated_at}</p>
            <Totals totals={data.totals} />
          </>
        )}
      </header>
      {files.length === 0 ? (
        <p className="empty">No files audited</p>
      ) : (
        files.map((file, i) => <FileCard file={file} key={i} />)
      )}
    </main>
  );
}
