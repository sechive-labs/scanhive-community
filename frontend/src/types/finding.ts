export type TriageStatus =
  | "To Verify"
  | "False Positive"
  | "Not Exploitable"
  | "Confirmed"
  | "Fixed";

export interface TriageHistoryEntry {
  id: number;
  triage_status: TriageStatus;
  comments: string | null;
  triaged_by: string | null;
  triaged_at: string;
}

export interface Finding {
  id: number;
  scan_id: string;
  tool: string;
  rule_id: string;
  title: string;
  severity: string;
  message: string;
  file_path: string;
  line_number: number | null;
  end_line: number | null;
  start_column: number | null;
  end_column: number | null;
  snippet: string | null;
  cwe: string | null;
  owasp: string | null;
  help_uri: string | null;
  fingerprint: string | null;
  result_status: "New" | "Recurrent";
  uploaded_at: string;
  triage_status: TriageStatus;
  triage_comments: string | null;
  triaged_by: string | null;
  triage_history: TriageHistoryEntry[];
}

export interface FindingsResponse {
  items: Finding[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}
