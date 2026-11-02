export interface Finding {
  check: string;
  severity: string;
  column: string | null;
  message: string;
  count: number;
  examples: string[];
}

export interface FileEntry {
  path: string;
  rows: number;
  columns: Record<string, string>;
  findings: Finding[];
}

export interface AuditData {
  generated_at: string;
  files: FileEntry[];
  totals: Record<string, number>;
}
