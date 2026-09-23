import { App, AutoComplete, Button, Card, Form, Input, Menu, Popconfirm, Table, Tag, Tooltip, Typography } from "antd";
import { Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getProject, getProjectAccess, updateProject, updateProjectAccess } from "../api/projectsApi";
import { getProfile } from "../api/iamApi";
import type { ProjectAccessAssignment, ProjectAccessGroup, ProjectAccessUser } from "../types/project";
import { getApiErrorMessage } from "../utils/apiError";

function errorMessage(error: unknown) {
  return getApiErrorMessage(error, "Unable to save settings.");
}

export function ProjectSettings({ projectId }: { projectId: string }) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [section, setSection] = useState("general");
  const [hasInitializedSection, setHasInitializedSection] = useState(false);
  const [assignments, setAssignments] = useState<ProjectAccessAssignment[]>([]);
  const [groupIds, setGroupIds] = useState<number[]>([]);
  const [userSearch, setUserSearch] = useState("");
  const [groupSearch, setGroupSearch] = useState("");
  const [form] = Form.useForm();
  const profileQuery = useQuery({ queryKey: ["iam-profile"], queryFn: getProfile });
  const projectQuery = useQuery({ queryKey: ["project", projectId], queryFn: () => getProject(projectId) });
  const accessQuery = useQuery({ queryKey: ["project-access", projectId], queryFn: () => getProjectAccess(projectId), enabled: section === "access" });

  const isOwner = Boolean(profileQuery.data && projectQuery.data && projectQuery.data.owner_id === profileQuery.data.id);
  const permissions = profileQuery.data?.effective_permissions ?? [];
  const canEditGeneral = isOwner || permissions.includes("projects.edit");
  const canManageAccess = isOwner || permissions.includes("projects.settings");

  // Land on whichever tab this user can actually use, once we know which
  // that is -- defaulting to "general" would silently strand an
  // access-only user (e.g. a custom role with only projects.settings) on a
  // read-only tab they can't save.
  useEffect(() => {
    if (hasInitializedSection || !profileQuery.data || !projectQuery.data) return;
    if (!canEditGeneral && canManageAccess) setSection("access");
    setHasInitializedSection(true);
  }, [hasInitializedSection, profileQuery.data, projectQuery.data, canEditGeneral, canManageAccess]);

  useEffect(() => {
    if (projectQuery.data) form.setFieldsValue({ name: projectQuery.data.name, description: projectQuery.data.description ?? "" });
  }, [form, projectQuery.data]);
  useEffect(() => {
    if (accessQuery.data) {
      setAssignments(accessQuery.data.assignments);
      setGroupIds(accessQuery.data.group_ids);
    }
  }, [accessQuery.data]);

  const generalMutation = useMutation({
    mutationFn: (values: { name: string; description: string }) => updateProject(projectId, values),
    onSuccess: async () => {
      message.success("Project settings updated.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["project-details", projectId] }),
        queryClient.invalidateQueries({ queryKey: ["project", projectId] }),
      ]);
    },
    onError: (error) => message.error(errorMessage(error)),
  });

  const accessMutation = useMutation({
    mutationFn: () => updateProjectAccess(projectId, assignments, groupIds),
    onSuccess: async () => {
      const before = new Set((accessQuery.data?.assignments ?? []).map((item) => item.user_id));
      const after = new Set(assignments.map((item) => item.user_id));
      const beforeGroups = new Set(accessQuery.data?.group_ids ?? []);
      const afterGroups = new Set(groupIds);
      const added = [...after].filter((id) => !before.has(id)).length + [...afterGroups].filter((id) => !beforeGroups.has(id)).length;
      const removed = [...before].filter((id) => !after.has(id)).length + [...beforeGroups].filter((id) => !afterGroups.has(id)).length;
      if (added && removed) message.success(`${added} access assignment${added === 1 ? "" : "s"} added and ${removed} removed.`);
      else if (added) message.success(`${added} access assignment${added === 1 ? "" : "s"} added.`);
      else if (removed) message.success(`${removed} access assignment${removed === 1 ? "" : "s"} removed.`);
      else message.info("Project access is already up to date.");
      await queryClient.invalidateQueries({ queryKey: ["project-access", projectId] });
    },
    onError: (error) => message.error(errorMessage(error)),
  });

  const assignedIds = useMemo(() => new Set(assignments.map((item) => item.user_id)), [assignments]);
  const assignedGroupIds = useMemo(() => new Set(groupIds), [groupIds]);
  const assignedUsers = (accessQuery.data?.users ?? []).filter((user) => assignedIds.has(user.id));
  const assignedGroups = (accessQuery.data?.groups ?? []).filter((group) => assignedGroupIds.has(group.id));
  const searchOptions = (accessQuery.data?.users ?? [])
    .filter((user) => !assignedIds.has(user.id) && `${user.email} ${user.first_name} ${user.last_name}`.toLowerCase().includes(userSearch.toLowerCase()))
    .map((user) => ({ value: String(user.id), label: <div className="access-user-option"><strong>{user.first_name} {user.last_name}</strong><span>{user.email}</span></div> }));
  const groupSearchOptions = (accessQuery.data?.groups ?? [])
    .filter((group) => !assignedGroupIds.has(group.id) && group.name.toLowerCase().includes(groupSearch.toLowerCase()))
    .map((group) => ({ value: String(group.id), label: <div className="access-user-option"><strong>{group.name}</strong><span>{group.member_count} member{group.member_count === 1 ? "" : "s"}</span></div> }));

  const columns = [
    {
      title: "User with access", key: "user", render: (_: unknown, user: ProjectAccessUser) => (
        <div className="access-user-cell"><strong>{user.first_name} {user.last_name}</strong><span>{user.email}</span></div>
      ),
    },
    {
      title: "IAM roles", dataIndex: "effective_role_names", key: "roles", render: (roles: string[]) => roles.length
        ? roles.map((role) => <Tag key={role}>{role}</Tag>)
        : <Typography.Text type="secondary">No IAM roles</Typography.Text>,
    },
    {
      title: "", key: "actions", width: 56, align: "right" as const, render: (_: unknown, user: ProjectAccessUser) => (
        <Popconfirm title="Remove project access?" description={`Remove ${user.email} from this project?`} onConfirm={() => setAssignments((current) => current.filter((item) => item.user_id !== user.id))}>
          <Button type="text" danger icon={<Trash2 size={15} />} aria-label={`Remove ${user.email}`} />
        </Popconfirm>
      ),
    },
  ];

  const groupColumns = [
    {
      title: "User group", key: "group", render: (_: unknown, group: ProjectAccessGroup) => (
        <div className="access-user-cell"><strong>{group.name}</strong><span>{group.member_count} member{group.member_count === 1 ? "" : "s"}</span></div>
      ),
    },
    {
      title: "IAM roles", dataIndex: "effective_role_names", key: "roles", render: (roles: string[]) => roles.length
        ? roles.map((role) => <Tag key={role}>{role}</Tag>)
        : <Typography.Text type="secondary">No IAM roles</Typography.Text>,
    },
    {
      title: "", key: "actions", width: 56, align: "right" as const, render: (_: unknown, group: ProjectAccessGroup) => (
        <Popconfirm title="Remove group access?" description={`Remove ${group.name} from this project?`} onConfirm={() => setGroupIds((current) => current.filter((id) => id !== group.id))}>
          <Button type="text" danger icon={<Trash2 size={15} />} aria-label={`Remove ${group.name}`} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div className="project-settings-ant-layout">
      <Card className="project-settings-ant-nav" size="small">
        <Menu
          mode="inline"
          selectedKeys={[section]}
          onSelect={({ key }) => setSection(key)}
          items={[
            {
              key: "general",
              label: canEditGeneral ? "General" : (
                <Tooltip title="You don't have permission to edit this project's details." placement="right">
                  <span>General</span>
                </Tooltip>
              ),
              disabled: !canEditGeneral,
            },
            {
              key: "access",
              label: canManageAccess ? "Access" : (
                <Tooltip title="You don't have permission to manage this project's access." placement="right">
                  <span>Access</span>
                </Tooltip>
              ),
              disabled: !canManageAccess,
            },
          ]}
        />
      </Card>

      {section === "general" ? (
        <Card className="project-settings-ant-card">
          <fieldset disabled={!canEditGeneral} className="project-settings-fieldset">
            <Form form={form} layout="vertical" requiredMark="optional" onFinish={(values) => generalMutation.mutate(values)}>
              <Form.Item label="Project name" name="name" rules={[{ required: true, message: "Enter a project name" }]}><Input maxLength={255} /></Form.Item>
              <Form.Item label="Description" name="description"><Input.TextArea rows={4} maxLength={1000} showCount /></Form.Item>
              <Form.Item className="settings-form-actions"><Button type="primary" htmlType="submit" disabled={!canEditGeneral} loading={generalMutation.isPending}>Save changes</Button></Form.Item>
            </Form>
          </fieldset>
        </Card>
      ) : (
        <Card className="project-settings-ant-card">
          <fieldset disabled={!canManageAccess} className="project-settings-fieldset">
            <Typography.Title level={5}>Users</Typography.Title>
            <AutoComplete
              className="project-access-autocomplete"
              value={userSearch}
              options={userSearch.trim() ? searchOptions : []}
              placeholder="Search users by name or email"
              onSearch={setUserSearch}
              onChange={setUserSearch}
              onSelect={(value) => { setAssignments((current) => [...current, { user_id: Number(value) }]); setUserSearch(""); }}
            />
            <Table<ProjectAccessUser>
              className="project-access-ant-table"
              rowKey="id"
              size="small"
              columns={columns}
              dataSource={assignedUsers}
              loading={accessQuery.isLoading}
              pagination={false}
              locale={{ emptyText: "No users have access yet" }}
            />
            <Typography.Title level={5}>User Groups</Typography.Title>
            <AutoComplete
              className="project-access-autocomplete"
              value={groupSearch}
              options={groupSearch.trim() ? groupSearchOptions : []}
              placeholder="Search user groups"
              onSearch={setGroupSearch}
              onChange={setGroupSearch}
              onSelect={(value) => { setGroupIds((current) => [...current, Number(value)]); setGroupSearch(""); }}
            />
            <Table<ProjectAccessGroup>
              className="project-access-ant-table"
              rowKey="id"
              size="small"
              columns={groupColumns}
              dataSource={assignedGroups}
              loading={accessQuery.isLoading}
              pagination={false}
              locale={{ emptyText: "No user groups have access yet" }}
            />
            <div className="settings-form-actions"><Button type="primary" disabled={!canManageAccess} loading={accessMutation.isPending} onClick={() => accessMutation.mutate()}>Save access</Button></div>
          </fieldset>
        </Card>
      )}
    </div>
  );
}
