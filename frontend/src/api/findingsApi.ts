import { apiClient } from "./client";
import type {
  Finding,
  FindingsResponse,
  TriageStatus,
} from "../types/finding";

export async function getScanFindings(
  projectId: string,
  scanId: string,
  page: number,
  pageSize: number,
  severity: string,
  resultStatus: string,
  triageStatus: string,
): Promise<FindingsResponse> {
  const response = await apiClient.get<FindingsResponse>(
    `/api/v1/projects/${projectId}/findings`,
    {
      params: {
        scan_id: scanId,
        page,
        page_size: pageSize,
        severity: severity || undefined,
        result_status: resultStatus || undefined,
        triage_status: triageStatus || undefined,
      },
    },
  );

  return response.data;
}

export async function getFindingDetails(
  projectId: string,
  findingId: number,
): Promise<Finding> {
  const response = await apiClient.get<Finding>(
    `/api/v1/projects/${projectId}/findings/${findingId}`,
  );
  return response.data;
}

export async function updateFindingTriage(
  projectId: string,
  findingId: number,
  triageStatus: TriageStatus,
  comments: string,
): Promise<Finding> {
  const response = await apiClient.put<Finding>(
    `/api/v1/projects/${projectId}/findings/${findingId}/triage`,
    {
      triage_status: triageStatus,
      comments,
    },
  );
  return response.data;
}
