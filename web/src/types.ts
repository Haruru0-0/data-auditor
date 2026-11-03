export interface Finding {
  check: string;
  severity: string;
  column: string | null;
  message: string;
  count: number;
  examples: string[];
}

export interface ColumnProfile {
  type: string;
  missing: number;
  distinct: number;
  min?: number | string | null;
  max?: number | string | null;
  mean?: number | null;
}

export interface FileEntry {
  path: string;
  rows: number;
  columns: Record<string, string>;
  findings: Finding[];
  score?: number;
  profile?: Record<string, ColumnProfile>;
}

export interface AuditData {
  generated_at: string;
  files: FileEntry[];
  totals: Record<string, number>;
}
