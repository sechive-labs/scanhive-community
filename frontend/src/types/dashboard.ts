export interface DashboardFilters {
  projects: Array<{ id: string; name: string }>;
  tools: string[];
  scan_types: string[];
}

export interface DashboardBreakdown {
  name: string;
  scans: number;
  findings: number;
}

export interface DashboardAnalytics {
  filters: DashboardFilters;
  summary: {
    projects: number;
    scans: number;
    findings: number;
    critical: number;
    high: number;
    confirmed: number;
  };
  severity: Array<{ name: string; value: number }>;
  by_project: DashboardBreakdown[];
  by_tool: DashboardBreakdown[];
  by_scan_type: DashboardBreakdown[];
  trend: Array<{
    period: string;
    label: string;
    scans: number;
    findings: number;
  }>;
}

export interface PortfolioFinding {
  id: number; project_id: string; project_name: string; scan_id: string; title: string;
  severity: string; result_status: "New" | "Recurrent"; triage_status: string;
  scan_type: string; tool: string; file_path: string; uploaded_at: string;
}

export interface PortfolioFindingsResponse {
  items: PortfolioFinding[]; page: number; page_size: number; total: number; total_pages: number;
  severity: Array<{ name: string; value: number }>;
  triage: Array<{ name: string; value: number }>;
  status: Array<{ name: string; value: number }>;
}
