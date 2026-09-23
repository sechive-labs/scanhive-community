export type ScanType =
  | "SAST"
  | "SCA"
  | "Secrets"
  | "Container Security"
  | "IaC"
  | "DAST";

export interface ScanHistoryItem {
  id: string;
  scan_type: ScanType;
  tool: string;
  filename: string;
  status: string;
  uploaded_at: string;
  findings: number;
}

export const SCAN_TYPES: ScanType[] = [
  "SAST",
  "SCA",
  "Secrets",
  "Container Security",
  "IaC",
  "DAST",
];

export interface ScanUploadResponse {
  scan_id: string;
  scan_type: ScanType;
  tool: string;
  filename: string;
  status: string;
  findings: number;
}
