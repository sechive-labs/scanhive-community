import { apiClient } from "./client";

import type {
  Project,
  ProjectCreateRequest,
  ProjectDetails,
  ProjectSummary,
  ProjectUpdateRequest,
  ProjectAccessAssignment,
  ProjectAccessResponse,
} from "../types/project";
import type { ScanHistoryItem, ScanType, ScanUploadResponse } from "../types/scan";

export async function getProjects(): Promise<ProjectSummary[]> {
  const response = await apiClient.get<ProjectSummary[]>(
    "/api/v1/projects",
  );

  return response.data;
}

export async function getProject(
  projectId: string,
): Promise<Project> {
  const response = await apiClient.get<Project>(
    `/api/v1/projects/${projectId}`,
  );

  return response.data;
}

export async function getProjectDetails(
  projectId: string,
): Promise<ProjectDetails> {
  const response = await apiClient.get<ProjectDetails>(
    `/api/v1/projects/${projectId}/project_details`,
  );

  return response.data;
}

export async function getProjectScans(
  projectId: string,
): Promise<ScanHistoryItem[]> {
  const response = await apiClient.get<ScanHistoryItem[]>(
    `/api/v1/projects/${projectId}/scans`,
  );

  return response.data;
}

export async function createProject(
  request: ProjectCreateRequest,
): Promise<Project> {
  const response = await apiClient.post<Project>(
    "/api/v1/projects",
    request,
  );

  return response.data;
}

export async function updateProject(
  projectId: string,
  request: ProjectUpdateRequest,
): Promise<Project> {
  const response = await apiClient.put<Project>(
    `/api/v1/projects/${projectId}`,
    request,
  );

  return response.data;
}

export async function deleteProject(
  projectId: string,
): Promise<void> {
  await apiClient.delete(
    `/api/v1/projects/${projectId}`,
  );
}

export async function getProjectAccess(projectId: string): Promise<ProjectAccessResponse> {
  const response = await apiClient.get<ProjectAccessResponse>(`/api/v1/projects/${projectId}/access`);
  return response.data;
}

export async function updateProjectAccess(projectId: string, assignments: ProjectAccessAssignment[], groupIds: number[]): Promise<ProjectAccessResponse> {
  const response = await apiClient.put<ProjectAccessResponse>(`/api/v1/projects/${projectId}/access`, { assignments, group_ids: groupIds });
  return response.data;
}

export async function exportProjectReport(projectId: string, format: "pdf" | "csv"): Promise<Blob> {
  const response = await apiClient.get(`/api/v1/projects/${projectId}/reports/${format}`, { responseType: "blob" });
  return response.data;
}

export async function exportScanReport(projectId: string, scanId: string, format: "pdf" | "csv"): Promise<Blob> {
  const response = await apiClient.get(`/api/v1/projects/${projectId}/scans/${scanId}/reports/${format}`, { responseType: "blob" });
  return response.data;
}

export async function deleteScan(scanId: string): Promise<void> {
  await apiClient.delete(`/api/v1/scans/${scanId}`);
}

export async function uploadScan(
  projectId: string,
  scanType: ScanType,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<ScanUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("scan_type", scanType);
  const response = await apiClient.post<ScanUploadResponse>(
    `/api/v1/scans/upload/${projectId}`,
    formData,
    {
      onUploadProgress: (progressEvent) => {
        if (!onProgress) return;
        const percent = progressEvent.total
          ? Math.round((progressEvent.loaded / progressEvent.total) * 100)
          : Math.round((progressEvent.progress ?? 0) * 100);
        onProgress(Math.min(percent, 100));
      },
    },
  );
  return response.data;
}
