export interface Project {
  id: string;
  name: string;
  description: string | null;
  owner_id: number;
}

export interface ProjectSummary extends Project {
  total_vulnerabilities: number;
  last_scan: string | null;
  scanners: string[] | null;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface SeveritySummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface ProjectDetails {
  project_id: string;
  project_name: string;
  total_scans: number;
  total_findings: number;
  severity: SeveritySummary;
  tools: Record<string, number>;
  last_scan: string | null;
}

export interface ProjectCreateRequest {
  name: string;
  description: string;
}

export interface ProjectUpdateRequest {
  name: string;
  description: string;
}

export interface ProjectAccessAssignment { user_id: number }
export interface ProjectAccessUser { id: number; email: string; first_name: string; last_name: string; effective_role_names: string[] }
export interface ProjectAccessGroup { id: number; name: string; description: string | null; member_count: number; effective_role_names: string[] }
export interface ProjectAccessResponse {
  users: ProjectAccessUser[];
  assignments: ProjectAccessAssignment[];
  groups: ProjectAccessGroup[];
  group_ids: number[];
}
