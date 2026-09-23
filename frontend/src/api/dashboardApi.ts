import type { DashboardAnalytics, PortfolioFindingsResponse } from "../types/dashboard";
import { apiClient } from "./client";

export interface DashboardFilterValues {
  projectId: string;
  tool: string;
  scanType: string;
}

export interface VulnerabilityFilters {
  projectId: string; severity: string; triageStatus: string; resultStatus: string; search: string; page: number; pageSize: number;
}

function vulnerabilityParams(filters: VulnerabilityFilters) {
  return { project_id: filters.projectId || undefined, severity: filters.severity || undefined, triage_status: filters.triageStatus || undefined, result_status: filters.resultStatus || undefined, search: filters.search || undefined };
}

export async function getPortfolioVulnerabilities(filters: VulnerabilityFilters): Promise<PortfolioFindingsResponse> {
  const response = await apiClient.get<PortfolioFindingsResponse>("/api/v1/dashboard/vulnerabilities", { params: { ...vulnerabilityParams(filters), page: filters.page, page_size: filters.pageSize } });
  return response.data;
}

export async function exportPortfolioVulnerabilities(format: "pdf" | "csv", filters: VulnerabilityFilters): Promise<Blob> {
  const response = await apiClient.get(`/api/v1/dashboard/vulnerabilities/reports/${format}`, { params: vulnerabilityParams(filters), responseType: "blob" });
  return response.data;
}

export async function getDashboardAnalytics(
  filters: DashboardFilterValues,
): Promise<DashboardAnalytics> {
  const response = await apiClient.get<DashboardAnalytics>(
    "/api/v1/dashboard/analytics",
    {
      params: {
        project_id: filters.projectId || undefined,
        tool: filters.tool || undefined,
        scan_type: filters.scanType || undefined,
      },
    },
  );
  return response.data;
}
