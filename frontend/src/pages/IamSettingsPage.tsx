import { App, Table } from "antd";
import {
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  useNavigate,
  useSearchParams,
} from "react-router-dom";

import {
  getRoles,
  getUsers,
  deleteRole,
  createGroup,
  getGroups,
  getGroupResources,
  updateGroup,
  deleteGroup,
  getOrganization,
  getInvitations,
  createInvitation,
  revokeInvitation,
} from "../api/iamApi";
import { GroupModal } from "../components/GroupModal";
import { InviteUserModal } from "../components/InviteUserModal";
import { LoadingState } from "../components/LoadingState";
import { usePermissions } from "../auth/usePermissions";
import { ApiKeysSection } from "./ApiKeysPage";
import type { IamGroup, IamRole, IamUser, Invitation } from "../types/iam";
import { getApiErrorMessage } from "../utils/apiError";
import { formatLocalDateTime } from "../utils/date";
import { copyToClipboard } from "../utils/clipboard";

type IamSection = "organization" | "users" | "roles" | "groups" | "api-keys";

const SECTIONS: Array<{
  id: IamSection;
  label: string;
}> = [
  { id: "organization", label: "General" },
  { id: "users", label: "Users" },
  { id: "roles", label: "Roles" },
  { id: "groups", label: "User Groups" },
  { id: "api-keys", label: "API Keys" },
];

function getErrorMessage(error: unknown): string {
  return getApiErrorMessage(error);
}

export function IamSettingsPage() {
  const { modal, message } = App.useApp();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedSectionValue = searchParams.get("section");
  const requestedActiveSection: IamSection = SECTIONS.some(
    (section) => section.id === requestedSectionValue,
  )
    ? (requestedSectionValue as IamSection)
    : "organization";
  const [roleError, setRoleError] = useState("");
  const [isGroupModalOpen, setGroupModalOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<IamGroup | null>(null);
  const [groupError, setGroupError] = useState("");
  const [isInviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteError, setInviteError] = useState("");

  const organizationQuery = useQuery({
    queryKey: ["organization"],
    queryFn: getOrganization,
    enabled: requestedActiveSection === "organization",
  });
  const { hasAnyIamPermission } = usePermissions();
  const canManageIam = hasAnyIamPermission();
  const activeSection: IamSection = canManageIam
    ? requestedActiveSection
    : "api-keys";
  const visibleSections = canManageIam
    ? SECTIONS
    : SECTIONS.filter((section) => section.id === "api-keys");

  const usersQuery = useQuery({
    queryKey: ["iam-users"],
    queryFn: getUsers,
    enabled: activeSection === "users" || activeSection === "groups",
  });

  const rolesQuery = useQuery({
    queryKey: ["iam-roles"],
    queryFn: getRoles,
    enabled: activeSection === "roles" || activeSection === "users" || activeSection === "groups",
  });

  const groupsQuery = useQuery({
    queryKey: ["iam-groups"],
    queryFn: getGroups,
    enabled: activeSection === "groups",
  });

  const groupResourcesQuery = useQuery({
    queryKey: ["iam-group-resources"],
    queryFn: getGroupResources,
    enabled: activeSection === "groups",
  });

  const invitationsQuery = useQuery({
    queryKey: ["iam-invitations"],
    queryFn: getInvitations,
    enabled: activeSection === "users",
  });

  const inviteMutation = useMutation({
    mutationFn: createInvitation,
    onSuccess: async (invitation) => {
      await queryClient.invalidateQueries({ queryKey: ["iam-invitations"] });
      setInviteModalOpen(false);
      setInviteError("");
      if (invitation.email_sent) {
        message.success(`Invitation email sent to ${invitation.email}.`);
      } else {
        message.info("Invitation created. Copy the link below to share it manually.");
      }
    },
    onError: (error) => setInviteError(getErrorMessage(error)),
  });

  const revokeInvitationMutation = useMutation({
    mutationFn: revokeInvitation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["iam-invitations"] });
    },
  });

  const roleDeleteMutation = useMutation({
    mutationFn: deleteRole,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["iam-roles"] });
      setRoleError("");
    },
    onError: (error) => setRoleError(getErrorMessage(error)),
  });

  const groupMutation = useMutation({
    mutationFn: (request: Parameters<typeof updateGroup>[1]) =>
      selectedGroup
        ? updateGroup(selectedGroup.id, request)
        : createGroup(request),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["iam-groups"] });
      setGroupModalOpen(false);
      setSelectedGroup(null);
      setGroupError("");
    },
    onError: (error) => setGroupError(getErrorMessage(error)),
  });

  const groupDeleteMutation = useMutation({
    mutationFn: deleteGroup,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["iam-groups"] });
      setGroupError("");
    },
    onError: (error) => setGroupError(getErrorMessage(error)),
  });

  function confirmDeleteRole(role: IamRole): void {
    modal.confirm({
      title: `Delete custom role ${role.name}?`,
      okText: "Delete role",
      okButtonProps: { danger: true },
      cancelText: "Cancel",
      centered: true,
      onOk: () => roleDeleteMutation.mutate(role.id),
    });
  }

  function confirmDeleteGroup(group: IamGroup): void {
    modal.confirm({
      title: `Delete user group ${group.name}?`,
      okText: "Delete group",
      okButtonProps: { danger: true },
      cancelText: "Cancel",
      centered: true,
      onOk: () => groupDeleteMutation.mutate(group.id),
    });
  }

  const userColumns = [
    { title: "Name", key: "name", render: (_: unknown, user: IamUser) => <strong>{user.first_name} {user.last_name}</strong> },
    { title: "Email", dataIndex: "email", key: "email" },
    {
      title: "Roles", key: "roles", render: (_: unknown, user: IamUser) => (
        user.roles.length
          ? <div className="iam-user-roles">{user.roles.map((role) => <span key={role.id}>{role.name}</span>)}</div>
          : <em>No roles</em>
      ),
    },
    {
      title: "Status", key: "status", render: (_: unknown, user: IamUser) => (
        <span className={`user-account-status ${user.is_active ? "enabled" : "disabled"}`}>{user.is_active ? "Enabled" : "Disabled"}</span>
      ),
    },
    {
      title: "", key: "actions", render: (_: unknown, user: IamUser) => (
        <div className="iam-user-actions">
          <button type="button" className="secondary-button iam-manage-roles" onClick={() => navigate(`/settings/iam/users/${user.id}/edit`)}>Edit user</button>
        </div>
      ),
    },
  ];

  const roleColumns = [
    { title: "Role name", key: "name", render: (_: unknown, role: IamRole) => <strong>{role.name}</strong> },
    {
      title: "Description", key: "description", render: (_: unknown, role: IamRole) => (
        <span className="iam-role-description" title={role.description}>{role.description}</span>
      ),
    },
    {
      title: "Type", key: "type", render: (_: unknown, role: IamRole) => (
        <span className={`iam-role-type ${role.locked ? "locked" : role.is_system ? "composite" : ""}`}>
          {role.locked ? "Default" : role.is_system ? "Composite Role" : "Custom"}
        </span>
      ),
    },
    {
      title: "", key: "actions", render: (_: unknown, role: IamRole) => (
        role.locked ? null : (
        <div className="iam-role-actions">
          <button type="button" className="icon-button" aria-label={`Edit ${role.name}`} onClick={() => navigate(`/settings/iam/roles/${role.id}/edit`)}>
            <Pencil size={15} />
          </button>
          <button
            type="button"
            className="icon-button danger-icon-button"
            aria-label={`Delete ${role.name}`}
            title="Delete role"
            disabled={roleDeleteMutation.isPending}
            onClick={() => confirmDeleteRole(role)}
          >
            <Trash2 size={15} />
          </button>
        </div>
        )
      ),
    },
  ];

  const groupColumns = [
    { title: "Group", key: "name", render: (_: unknown, group: IamGroup) => <strong>{group.name}</strong> },
    { title: "Members", key: "members", render: (_: unknown, group: IamGroup) => group.users.map((user) => user.name).join(", ") || "No members" },
    { title: "Roles", key: "roles", render: (_: unknown, group: IamGroup) => group.roles.map((role) => role.name).join(", ") || "No roles" },
    { title: "Resource access", key: "resources", render: (_: unknown, group: IamGroup) => `${group.projects.length} projects` },
    { title: "Created by", key: "created_by", render: (_: unknown, group: IamGroup) => group.created_by || "Not applicable" },
    {
      title: "", key: "actions", render: (_: unknown, group: IamGroup) => (
        <div className="iam-role-actions">
          <button type="button" className="icon-button" aria-label={`Edit ${group.name}`} onClick={() => { setSelectedGroup(group); setGroupModalOpen(true); }}>
            <Pencil size={15} />
          </button>
          <button type="button" className="icon-button danger-icon-button" aria-label={`Delete ${group.name}`} disabled={groupDeleteMutation.isPending} onClick={() => confirmDeleteGroup(group)}>
            <Trash2 size={15} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="page-container iam-page">
      <div className="page-heading iam-heading">
        <div>
          <h1>Identity &amp; Access Management</h1>
        </div>
      </div>

      <nav className="iam-tabs" aria-label="Identity and access settings">
        {visibleSections.map((section) => (
          <button
            type="button"
            key={section.id}
            className={activeSection === section.id ? "active" : ""}
            onClick={() => {
              setSearchParams({ section: section.id });
            }}
          >
            {section.label}
          </button>
        ))}
      </nav>

      {activeSection === "api-keys" && <ApiKeysSection />}

      {activeSection === "organization" && (
        <section className="iam-panel organization-settings-panel">
          {organizationQuery.isLoading && <LoadingState size={20} compact>Loading organization...</LoadingState>}
          {organizationQuery.data && (
            <div className="organization-settings-form">
              <label className="form-group">
                <span>Organization name</span>
                <input className="form-input" value={organizationQuery.data.name} readOnly aria-readonly="true" />
              </label>
            </div>
          )}
        </section>
      )}

      {activeSection === "users" && (
        <section className="iam-panel">
          <div className="iam-panel-toolbar actions-only">
            <button
              type="button"
              className="primary-button small"
              onClick={() => { setInviteError(""); setInviteModalOpen(true); }}
            >
              <Plus size={16} />
              Invite member
            </button>
          </div>

          {usersQuery.isLoading && (
            <LoadingState size={20} compact>Loading users...</LoadingState>
          )}
          {usersQuery.isError && (
            <div className="alert-error">Unable to load users.</div>
          )}
          {usersQuery.data && (
            <Table<IamUser>
              rowKey="id"
              columns={userColumns}
              dataSource={usersQuery.data}
              pagination={false}
              locale={{ emptyText: "No users found." }}
            />
          )}

          {(invitationsQuery.data ?? []).length > 0 && (
            <div className="pending-invitations">
              <h3>Pending invitations</h3>
              <Table<Invitation>
                rowKey="id"
                pagination={false}
                dataSource={(invitationsQuery.data ?? []).filter((invitation) => invitation.status !== "accepted")}
                locale={{ emptyText: "No pending invitations." }}
                columns={[
                  { title: "Email", dataIndex: "email", key: "email" },
                  {
                    title: "Roles", key: "roles", render: (_: unknown, invitation: Invitation) => (
                      invitation.roles.length
                        ? <div className="iam-user-roles">{invitation.roles.map((role) => <span key={role.id}>{role.name}</span>)}</div>
                        : <em>No roles</em>
                    ),
                  },
                  { title: "Invited by", key: "invited_by", render: (_: unknown, invitation: Invitation) => invitation.invited_by ?? "Not applicable" },
                  {
                    title: "Status", key: "status", render: (_: unknown, invitation: Invitation) => (
                      <span className={`user-account-status ${invitation.status === "pending" ? "enabled" : "disabled"}`}>{invitation.status}</span>
                    ),
                  },
                  { title: "Expires", key: "expires_at", render: (_: unknown, invitation: Invitation) => formatLocalDateTime(invitation.expires_at) },
                  {
                    title: "", key: "actions", render: (_: unknown, invitation: Invitation) => (
                      <div className="iam-user-actions">
                        {invitation.status === "pending" && (
                          <>
                            <button
                              type="button"
                              className="secondary-button"
                              onClick={async () => {
                                const succeeded = await copyToClipboard(
                                  `${window.location.origin}/accept-invite/${invitation.token}`,
                                );
                                if (succeeded) {
                                  message.success("Invite link copied.");
                                } else {
                                  message.error("Unable to copy automatically. Please copy the link manually.");
                                }
                              }}
                            >
                              Copy link
                            </button>
                            <button
                              type="button"
                              className="secondary-button"
                              disabled={revokeInvitationMutation.isPending}
                              onClick={() => revokeInvitationMutation.mutate(invitation.id)}
                            >
                              Revoke
                            </button>
                          </>
                        )}
                      </div>
                    ),
                  },
                ]}
              />
            </div>
          )}
        </section>
      )}

      {activeSection === "roles" && (
        <section className="iam-panel">
          <div className="iam-panel-toolbar actions-only">
            <button
              type="button"
              className="primary-button small"
              onClick={() => navigate("/settings/iam/roles/new")}
            >
              <Plus size={16} />
              Create custom role
            </button>
          </div>

          {roleError && <div className="alert-error">{roleError}</div>}

          {rolesQuery.isLoading && (
            <LoadingState size={20} compact>Loading roles...</LoadingState>
          )}

          {rolesQuery.isError && (
            <div className="alert-error">Unable to load roles.</div>
          )}

          {rolesQuery.data && (
            <Table<IamRole>
              rowKey="id"
              columns={roleColumns}
              dataSource={rolesQuery.data}
              pagination={{ pageSize: 10, hideOnSinglePage: true }}
              locale={{ emptyText: "No custom roles created yet." }}
            />
          )}
        </section>
      )}

      {activeSection === "groups" && (
        <section className="iam-panel">
          <div className="iam-panel-toolbar actions-only">
            <button
              type="button"
              className="primary-button small"
              onClick={() => { setSelectedGroup(null); setGroupModalOpen(true); }}
            >
              <Plus size={16} /> Create group
            </button>
          </div>
          {groupError && <div className="alert-error">{groupError}</div>}
          {groupsQuery.isLoading && (
            <LoadingState size={20} compact>Loading groups...</LoadingState>
          )}
          {groupsQuery.data && (
            <Table<IamGroup>
              rowKey="id"
              columns={groupColumns}
              dataSource={groupsQuery.data}
              pagination={false}
              locale={{ emptyText: "No groups created yet." }}
            />
          )}
        </section>
      )}


      <GroupModal
        isOpen={isGroupModalOpen}
        isSubmitting={groupMutation.isPending}
        users={(usersQuery.data ?? []).map((user) => ({ id: user.id, name: user.email }))}
        roles={rolesQuery.data ?? []}
        projects={groupResourcesQuery.data?.projects ?? []}
        group={selectedGroup}
        onClose={() => { setGroupModalOpen(false); setSelectedGroup(null); }}
        onSubmit={async (request) => {
          await groupMutation.mutateAsync(request);
        }}
      />

      <InviteUserModal
        isOpen={isInviteModalOpen}
        isSubmitting={inviteMutation.isPending}
        error={inviteError}
        roles={rolesQuery.data ?? []}
        onClose={() => { setInviteModalOpen(false); setInviteError(""); }}
        onSubmit={async (request) => {
          await inviteMutation.mutateAsync(request);
        }}
      />

    </div>
  );
}
