export interface IamUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  effective_permissions: string[];
  roles: IamRole[];
  organization_id: number;
  organization_name: string;
}

export interface Organization {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
}

export interface Invitation {
  id: number;
  email: string;
  status: "pending" | "accepted" | "revoked" | "expired";
  token: string;
  roles: IamRole[];
  invited_by: string | null;
  created_at: string;
  expires_at: string;
  email_sent: boolean | null;
}

export interface InvitationCreateRequest {
  email: string;
  role_ids: number[];
}

export interface IamGroup {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  created_by: string | null;
  users: GroupItem[];
  roles: GroupItem[];
  projects: GroupItem[];
}

export interface GroupItem { id: number | string; name: string }

export interface GroupResources {
  projects: GroupItem[];
}

export interface GroupCreateRequest {
  name: string;
  description: string;
  user_ids: number[];
}

export interface GroupRequest extends GroupCreateRequest {
  role_ids: number[];
  project_ids: string[];
}

export interface ProfileUpdateRequest {
  first_name: string;
  last_name: string;
}

export interface UserAdminUpdateRequest extends ProfileUpdateRequest {
  email: string;
  is_active: boolean;
  role_ids: number[];
}

export interface IamRole {
  id: number;
  name: string;
  description: string;
  permissions: string[];
  is_system: boolean;
  locked: boolean;
  included_roles: GroupItem[];
  effective_permissions: string[];
}

export interface RoleRequest {
  name: string;
  description: string;
  permissions: string[];
  included_role_ids: number[];
}
