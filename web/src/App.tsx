import { useEffect, useState, type ReactNode } from "react";
import { MotionConfig, AnimatePresence, animate, motion, useReducedMotion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Separator } from "@/components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { AuditData, FileEntry, Finding } from "./types";

// A regex, not a string constant: the Python side replaces every literal
// placeholder in the file, so the bundle must not contain it.
const PLACEHOLDER = /^__AUDIT_DATA_{2}$/;
const KNOWN = ["error", "warning", "info"] as const;

type BadgeVariant = "destructive" | "outline" | "secondary";

// Fixed whitelist: class names, variants and symbols never come from the data.
const SEVERITY_STYLE: Record<string, { symbol: string; cls: string; variant: BadgeVariant; color: string }> = {
  error: { symbol: "✖", cls: "sev-error", variant: "destructive", color: "" },
  warning: { symbol: "▲", cls: "sev-warning", variant: "outline", color: "text-sev-warning" },
  info: { symbol: "ℹ", cls: "sev-info", variant: "outline", color: "text-sev-info" },
};
const FALLBACK_STYLE = { symbol: "•", cls: "sev-unknown", variant: "secondary" as BadgeVariant, color: "" };
const EXAMPLES_SHOWN = 3;
const FAST = 0.3; // seconds; every animation stays under 400 ms

// Entrance props: with reduced motion nothing starts offset or transparent.
function useEnter(offset: number, delay: number) {
  const reduce = useReducedMotion();
  return {
    initial: reduce ? (false as const) : { opacity: 0, y: offset },
    animate: { opacity: 1, y: 0 },
    transition: { duration: reduce ? 0 : FAST, delay: reduce ? 0 : delay },
  };
}

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
  const { symbol, cls, variant, color } = styleFor(severity);
  return (
    <Badge variant={variant} className={`sev ${cls} ${color}`}>
      {`${symbol} ${severity}`}
    </Badge>
  );
}

function CountUp({ value }: { value: unknown }) {
  const reduce = useReducedMotion();
  const target = typeof value === "number" && Number.isFinite(value) ? value : null;
  const [shown, setShown] = useState<number | null>(reduce ? target : target === null ? null : 0);
  useEffect(() => {
    if (target === null) return;
    if (reduce) {
      setShown(target);
      return;
    }
    const controls = animate(0, target, {
      duration: 0.4,
      ease: "easeOut",
      onUpdate: (v) => setShown(Math.round(v)),
      onComplete: () => setShown(target),
    });
    return () => controls.stop();
  }, [target, reduce]);
  return <strong>{String(target === null ? (value ?? 0) : shown)}</strong>;
}

function Total({ k, i, value }: { k: string; i: number; value: unknown }) {
  const enter = useEnter(6, Math.min(i, 8) * 0.04);
  return (
    <motion.span className="total inline-flex items-center gap-1.5" {...enter}>
      <Severity severity={k} /> <CountUp value={value} />
    </motion.span>
  );
}

function Totals({ totals }: { totals: Record<string, number> }) {
  const extra = Object.keys(totals)
    .filter((k) => !(KNOWN as readonly string[]).includes(k))
    .sort();
  const keys = [...KNOWN, ...extra];
  return (
    <p className="my-3 flex flex-wrap gap-x-5 gap-y-2" data-testid="totals">
      {keys.map((key, i) => (
        <Total k={key} i={i} value={totals[key] ?? 0} key={key} />
      ))}
    </p>
  );
}

const CHIP = "example mr-1.5 mb-1 inline-block rounded bg-muted px-1.5 py-0.5 font-mono text-xs [overflow-wrap:anywhere]";

function Examples({ examples }: { examples: string[] }) {
  const [open, setOpen] = useState(false);
  const reduce = useReducedMotion();
  const first = examples.slice(0, EXAMPLES_SHOWN);
  const more = examples.slice(EXAMPLES_SHOWN);
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      {first.map((ex, j) => (
        <code className={CHIP} key={j}>
          {ex}
        </code>
      ))}
      <AnimatePresence initial={false}>
        {open && (
          <CollapsibleContent forceMount asChild>
            <motion.div
              className="overflow-hidden"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: reduce ? 0 : FAST }}
            >
              {more.map((ex, j) => (
                <code className={CHIP} key={j}>
                  {ex}
                </code>
              ))}
            </motion.div>
          </CollapsibleContent>
        )}
      </AnimatePresence>
      {more.length > 0 && (
        <CollapsibleTrigger asChild>
          <button type="button" className="text-xs underline underline-offset-2 hover:text-muted-foreground">
            {open ? "show fewer" : `show all ${examples.length}`}
          </button>
        </CollapsibleTrigger>
      )}
    </Collapsible>
  );
}

const MotionRow = motion.create(TableRow);

function Row({ i, children }: { i: number; children: ReactNode }) {
  const enter = useEnter(6, Math.min(i, 10) * 0.03);
  return <MotionRow {...enter}>{children}</MotionRow>;
}

function FindingsTable({ findings }: { findings: Finding[] }) {
  return (
    <Table className="min-w-[36rem]">
      <TableHeader>
        <TableRow>
          <TableHead>Severity</TableHead>
          <TableHead>Check</TableHead>
          <TableHead>Column</TableHead>
          <TableHead>Message</TableHead>
          <TableHead className="text-right">Count</TableHead>
          <TableHead>Examples</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {findings.map((f, i) => (
          <Row key={i} i={i}>
            <TableCell>
              <Severity severity={String(f.severity)} />
            </TableCell>
            <TableCell>{f.check}</TableCell>
            <TableCell>{f.column ?? ""}</TableCell>
            <TableCell className="whitespace-normal">{f.message}</TableCell>
            <TableCell className="num text-right">{f.count}</TableCell>
            <TableCell className="whitespace-normal">
              <Examples examples={f.examples ?? []} />
            </TableCell>
          </Row>
        ))}
      </TableBody>
    </Table>
  );
}

function FileCard({ file, index }: { file: FileEntry; index: number }) {
  const columnCount = Object.keys(file.columns ?? {}).length;
  const findings = file.findings ?? [];
  const enter = useEnter(12, Math.min(index, 8) * 0.06);
  return (
    <motion.div {...enter}>
      <Card className="my-4">
        <CardHeader>
          <h2 className="path font-mono text-lg font-semibold [overflow-wrap:anywhere]">{file.path}</h2>
          <p className="meta text-sm text-muted-foreground">
            {file.rows} rows, {columnCount} columns
          </p>
        </CardHeader>
        <Separator />
        <CardContent>
          {findings.length === 0 ? (
            <p className="clean text-muted-foreground">No problems found</p>
          ) : (
            <FindingsTable findings={findings} />
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function App({ data }: { data: AuditData | null }) {
  const files = data?.files ?? [];
  return (
    <MotionConfig reducedMotion="user">
      <main className="mx-auto max-w-6xl p-4">
        <header>
          <h1 className="text-2xl font-semibold">Data audit</h1>
          {data && files.length > 0 && (
            <>
              <p className="generated text-sm text-muted-foreground">Generated at {data.generated_at}</p>
              <Totals totals={data.totals} />
            </>
          )}
        </header>
        {files.length === 0 ? (
          <p className="empty text-muted-foreground">No files audited</p>
        ) : (
          files.map((file, i) => <FileCard file={file} index={i} key={i} />)
        )}
      </main>
    </MotionConfig>
  );
}
