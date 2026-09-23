import { apiClient } from "./client";
import type {
  IamUser,
  IamRole,
  RoleRequest,
  IamGroup,
  GroupRequest,
  GroupCreateRequest,
  GroupResources,
  ProfileUpdateRequest,
  UserAdminUpdateRequest,
  Organization,
  Invitation,
  InvitationCreateRequest,
} from "../types/iam";

export async function getProfile(): Promise<IamUser> {
  const response = await apiClient.get<IamUser>("/api/v1/iam/profile");
  return response.data;
}

export async function updateProfile(request: ProfileUpdateRequest): Promise<IamUser> {
  const response = await apiClient.put<IamUser>("/api/v1/iam/profile", request);
  return response.data;
}

export async function getOrganization(): Promise<Organization> {
  const response = await apiClient.get<Organization>("/api/v1/iam/organization");
  return response.data;
}

export async function updateOrganization(name: string): Promise<Organization> {
  const response = await apiClient.put<Organization>("/api/v1/iam/organization", { name });
  return response.data;
}

export async function getInvitations(): Promise<Invitation[]> {
  const response = await apiClient.get<Invitation[]>("/api/v1/iam/invitations");
  return response.data;
}

export async function createInvitation(request: InvitationCreateRequest): Promise<Invitation> {
  const response = await apiClient.post<Invitation>("/api/v1/iam/invitations", request);
  return response.data;
}

export async function revokeInvitation(invitationId: number): Promise<void> {
  await apiClient.delete(`/api/v1/iam/invitations/${invitationId}`);
}

export async function getUsers(): Promise<IamUser[]> {
  const response = await apiClient.get<IamUser[]>("/api/v1/iam/users");
  return response.data;
}

export async function getUser(userId: number): Promise<IamUser> {
  const response = await apiClient.get<IamUser>(`/api/v1/iam/users/${userId}`);
  return response.data;
}

export async function getRoles(): Promise<IamRole[]> {
  const response = await apiClient.get<IamRole[]>("/api/v1/iam/roles");
  return response.data;
}

export async function getRole(roleId: number): Promise<IamRole> {
  const response = await apiClient.get<IamRole>(
    `/api/v1/iam/roles/${roleId}`,
  );
  return response.data;
}

export async function createRole(
  request: RoleRequest,
): Promise<IamRole> {
  const response = await apiClient.post<IamRole>(
    "/api/v1/iam/roles",
    request,
  );
  return response.data;
}

export async function updateRole(
  roleId: number,
  request: RoleRequest,
): Promise<IamRole> {
  const response = await apiClient.put<IamRole>(
    `/api/v1/iam/roles/${roleId}`,
    request,
  );
  return response.data;
}

export async function deleteRole(roleId: number): Promise<void> {
  await apiClient.delete(`/api/v1/iam/roles/${roleId}`);
}

export async function assignUserRoles(
  userId: number,
  roleIds: number[],
): Promise<IamUser> {
  const response = await apiClient.put<IamUser>(
    `/api/v1/iam/users/${userId}/roles`,
    { role_ids: roleIds },
  );
  return response.data;
}

export async function updateUser(userId: number, request: UserAdminUpdateRequest): Promise<IamUser> {
  const response = await apiClient.put<IamUser>(`/api/v1/iam/users/${userId}`, request);
  return response.data;
}

export async function getGroups(): Promise<IamGroup[]> {
  const response = await apiClient.get<IamGroup[]>("/api/v1/iam/groups");
  return response.data;
}

export async function getGroupResources(): Promise<GroupResources> {
  const response = await apiClient.get<GroupResources>("/api/v1/iam/group-resources");
  return response.data;
}

export async function createGroup(
  request: GroupCreateRequest,
): Promise<IamGroup> {
  const response = await apiClient.post<IamGroup>(
    "/api/v1/iam/groups",
    request,
  );
  return response.data;
}

export async function updateGroup(groupId: number, request: GroupRequest): Promise<IamGroup> {
  const response = await apiClient.put<IamGroup>(`/api/v1/iam/groups/${groupId}`, request);
  return response.data;
}

export async function deleteGroup(groupId: number): Promise<void> {
  await apiClient.delete(`/api/v1/iam/groups/${groupId}`);
}
