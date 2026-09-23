import { ArrowLeft, ChevronDown, ChevronRight, RefreshCw, X } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getRoles, getUser, updateUser } from "../api/iamApi";
import { getApiErrorMessage } from "../utils/apiError";

function errorMessage(error: unknown) {
  return getApiErrorMessage(error, "Unable to save user.");
}

export function UserEditorPage() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const id = Number(userId);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [accountDisabled, setAccountDisabled] = useState(false);
  const [roleIds, setRoleIds] = useState<number[]>([]);
  const [rolesExpanded, setRolesExpanded] = useState(false);
  const [roleSearch, setRoleSearch] = useState("");

  const userQuery = useQuery({ queryKey: ["iam-user", id], queryFn: () => getUser(id), enabled: Number.isInteger(id) && id > 0 });
  const rolesQuery = useQuery({ queryKey: ["iam-roles"], queryFn: getRoles });

  useEffect(() => {
    if (!userQuery.data) return;
    setFirstName(userQuery.data.first_name);
    setLastName(userQuery.data.last_name);
    setEmail(userQuery.data.email);
    setAccountDisabled(!userQuery.data.is_active);
    setRoleIds(userQuery.data.roles.map((role) => role.id));
  }, [userQuery.data]);

  const mutation = useMutation({
    mutationFn: () => updateUser(id, { first_name: firstName.trim(), last_name: lastName.trim(), email: email.trim(), is_active: !accountDisabled, role_ids: roleIds }),
    onSuccess: async (updatedUser) => {
      queryClient.setQueryData(["iam-user", id], updatedUser);
      queryClient.setQueryData(
        ["iam-users"],
        (users: (typeof updatedUser)[] | undefined) => users?.map((user) => user.id === updatedUser.id ? updatedUser : user),
      );
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["iam-user", id] }),
        queryClient.invalidateQueries({ queryKey: ["iam-users"] }),
      ]);
      navigate("/settings/iam?section=users");
    },
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    await mutation.mutateAsync();
  }

  const allRoles = rolesQuery.data ?? [];
  const effectivePermissionCount = new Set(
    allRoles
      .filter((role) => roleIds.includes(role.id))
      .flatMap((role) => role.effective_permissions),
  ).size;

  const selectedRoles = roleIds
    .map((roleId) => allRoles.find((role) => role.id === roleId))
    .filter((role): role is NonNullable<typeof role> => Boolean(role));

  const normalizedRoleSearch = roleSearch.trim().toLowerCase();
  const availableRoles = allRoles.filter((role) =>
    !roleIds.includes(role.id) &&
    (!normalizedRoleSearch ||
      role.name.toLowerCase().includes(normalizedRoleSearch) ||
      role.description.toLowerCase().includes(normalizedRoleSearch)),
  );

  function addRole(roleId: number): void {
    setRoleIds((current) => current.includes(roleId) ? current : [...current, roleId]);
  }

  function removeRole(roleId: number): void {
    setRoleIds((current) => current.filter((id) => id !== roleId));
  }

  return (
    <div className="page-container role-editor-page user-editor-page">
      <Link to="/settings/iam?section=users" className="back-link"><ArrowLeft size={17} /> Back to users</Link>
      <div className="page-heading role-editor-heading"><div><h1>Edit user</h1></div></div>

      {userQuery.isLoading && <div className="loading-state"><RefreshCw className="spin" size={22} /> Loading user...</div>}
      {userQuery.isError && <div className="alert-error">Unable to load this user.</div>}

      {userQuery.data && (
        <form className="role-editor-form" onSubmit={submit}>
          {mutation.isError && <div className="alert-error">{errorMessage(mutation.error)}</div>}
          <section className="role-editor-panel">
            <div className="role-editor-panel-heading"><div><h2>User details</h2></div></div>
            <div className="user-editor-fields">
              <label className="form-group"><span>First name</span><input className="form-input" value={firstName} onChange={(e) => setFirstName(e.target.value)} required /></label>
              <label className="form-group"><span>Last name</span><input className="form-input" value={lastName} onChange={(e) => setLastName(e.target.value)} /></label>
              <label className="form-group user-editor-email"><span>Email address</span><input className="form-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
            </div>
            <label className={`user-status-toggle user-editor-status ${accountDisabled ? "account-disabled" : ""}`}>
              <input type="checkbox" checked={accountDisabled} onChange={(e) => setAccountDisabled(e.target.checked)} />
              <span><strong>Account disabled</strong><small>Block password sign-in, API keys, and all existing authenticated sessions.</small></span>
            </label>
          </section>

          <section className="role-editor-panel">
            <button
              type="button"
              className="role-editor-panel-heading role-section-toggle"
              onClick={() => setRolesExpanded((current) => !current)}
            >
              {rolesExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <div>
                <h2>Role mapping</h2>
                <p>
                  {roleIds.length} role{roleIds.length === 1 ? "" : "s"} assigned.
                  {roleIds.length ? ` ${effectivePermissionCount} total permission${effectivePermissionCount === 1 ? "" : "s"}.` : ""}
                </p>
              </div>
            </button>

            {rolesExpanded && (
              allRoles.length ? (
                <div className="role-picker">
                  <div className="role-picker-available">
                    <input
                      type="search"
                      className="group-member-search"
                      value={roleSearch}
                      placeholder="Search roles..."
                      aria-label="Search roles"
                      onChange={(event) => setRoleSearch(event.target.value)}
                    />
                    <div className="role-picker-list">
                      {availableRoles.map((role) => (
                        <button
                          type="button"
                          key={role.id}
                          className="role-picker-item"
                          onClick={() => addRole(role.id)}
                        >
                          <span className="role-picker-item-name">{role.name}</span>
                          <span className="role-picker-item-description">{role.description}</span>
                        </button>
                      ))}
                      {!availableRoles.length && (
                        <div className="role-picker-empty">
                          {normalizedRoleSearch ? "No roles match your search." : "All roles have been added."}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="role-picker-selected">
                    <span className="role-picker-selected-label">Added roles</span>
                    {selectedRoles.length ? (
                      <div className="role-chip-list">
                        {selectedRoles.map((role) => (
                          <span key={role.id} className="role-chip">
                            {role.name}
                            <button
                              type="button"
                              aria-label={`Remove ${role.name}`}
                              onClick={() => removeRole(role.id)}
                            >
                              <X size={12} />
                            </button>
                          </span>
                        ))}
                      </div>
                    ) : (
                      <small className="role-picker-empty-hint">No roles added yet.</small>
                    )}
                  </div>
                </div>
              ) : (
                <small>No roles exist yet to assign.</small>
              )
            )}
          </section>

          <div className="role-editor-actions"><Link to="/settings/iam?section=users" className="secondary-button">Cancel</Link><button type="submit" className="primary-button small" disabled={mutation.isPending}>{mutation.isPending ? "Saving..." : "Save user"}</button></div>
        </form>
      )}
    </div>
  );
}
