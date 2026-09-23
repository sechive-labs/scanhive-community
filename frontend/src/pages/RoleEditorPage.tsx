import { ArrowLeft, ChevronDown, ChevronRight, X } from "lucide-react";
import {
  type FormEvent,
  useEffect,
  useState,
} from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  createRole,
  getRole,
  getRoles,
  updateRole,
} from "../api/iamApi";
import { LoadingState } from "../components/LoadingState";
import { getApiErrorMessage } from "../utils/apiError";

function getErrorMessage(error: unknown): string {
  return getApiErrorMessage(error, "Unable to save role.");
}

export function RoleEditorPage() {
  const { roleId } = useParams();
  const navigate = useNavigate();
  const parsedRoleId = Number(roleId);
  const isEditing = Boolean(roleId);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [permissions, setPermissions] = useState<string[]>([]);
  const [includedRoleIds, setIncludedRoleIds] = useState<number[]>([]);
  const [validationError, setValidationError] = useState("");
  const [rolesExpanded, setRolesExpanded] = useState(false);
  const [roleSearch, setRoleSearch] = useState("");

  const roleQuery = useQuery({
    queryKey: ["iam-role", parsedRoleId],
    queryFn: () => getRole(parsedRoleId),
    enabled: isEditing && Number.isInteger(parsedRoleId),
  });

  const rolesQuery = useQuery({ queryKey: ["iam-roles"], queryFn: getRoles });

  useEffect(() => {
    if (!roleQuery.data) return;
    setName(roleQuery.data.name);
    setDescription(roleQuery.data.description);
    setPermissions(roleQuery.data.permissions);
    setIncludedRoleIds(roleQuery.data.included_roles.map((role) => Number(role.id)));
  }, [roleQuery.data]);

  const isLocked = Boolean(roleQuery.data?.locked);

  const saveMutation = useMutation({
    mutationFn: () => {
      const request = {
        name: name.trim(),
        description: description.trim(),
        permissions,
        included_role_ids: includedRoleIds,
      };
      return isEditing
        ? updateRole(parsedRoleId, request)
        : createRole(request);
    },
    onSuccess: () => navigate("/settings/iam?section=roles"),
  });

  const includableRoles = (rolesQuery.data ?? []).filter((role) => role.id !== parsedRoleId);
  const effectivePermissionCount = new Set([
    ...permissions,
    ...includableRoles
      .filter((role) => includedRoleIds.includes(role.id))
      .flatMap((role) => role.effective_permissions),
  ]).size;

  const selectedRoles = includedRoleIds
    .map((id) => includableRoles.find((role) => role.id === id))
    .filter((role): role is NonNullable<typeof role> => Boolean(role));

  const normalizedSearch = roleSearch.trim().toLowerCase();
  const availableRoles = includableRoles.filter((role) =>
    !includedRoleIds.includes(role.id) &&
    (!normalizedSearch ||
      role.name.toLowerCase().includes(normalizedSearch) ||
      role.description.toLowerCase().includes(normalizedSearch)),
  );

  function addRole(roleId: number): void {
    setIncludedRoleIds((current) => current.includes(roleId) ? current : [...current, roleId]);
  }

  function removeRole(roleId: number): void {
    setIncludedRoleIds((current) => current.filter((id) => id !== roleId));
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (!name.trim() || !description.trim()) {
      setValidationError("Role name and description are required.");
      return;
    }

    setValidationError("");
    await saveMutation.mutateAsync();
  }

  return (
    <div className="page-container role-editor-page">
      <Link to="/settings/iam?section=roles" className="back-link">
        <ArrowLeft size={17} />
        Back to roles
      </Link>

      <div className="page-heading role-editor-heading">
        <div>
          <h1>{isEditing ? (isLocked ? "View role" : "Edit role") : "Create custom role"}</h1>
        </div>
      </div>

      {roleQuery.isLoading && (
        <LoadingState size={22}>Loading role...</LoadingState>
      )}

      {roleQuery.isError && (
        <div className="alert-error">Unable to load this role.</div>
      )}

      {isLocked && (
        <div className="alert-error role-locked-notice">
          This is a default role and cannot be edited or deleted. Compose a custom role that includes it instead.
        </div>
      )}

      {(!isEditing || roleQuery.data) && (
        <form className="role-editor-form" onSubmit={handleSubmit}>
          {(validationError || saveMutation.isError) && (
            <div className="alert-error">
              {validationError || getErrorMessage(saveMutation.error)}
            </div>
          )}

          <fieldset className="role-editor-fieldset" disabled={isLocked}>

          <section className="role-editor-panel role-basics-panel">
            <div className="role-editor-panel-heading">
              <div>
                <h2>Role details</h2>
              </div>
            </div>
            <div className="role-editor-fields">
              <label className="form-group">
                <span>Role name</span>
                <input
                  className="form-input"
                  value={name}
                  maxLength={100}
                  placeholder="Release Security Reviewer"
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
              <label className="form-group">
                <span>Description</span>
                <textarea
                  className="form-input form-textarea"
                  value={description}
                  maxLength={500}
                  rows={4}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="role-editor-panel">
            <button
              type="button"
              className="role-editor-panel-heading role-section-toggle"
              onClick={() => setRolesExpanded((current) => !current)}
            >
              {rolesExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <div>
                <h2>Roles</h2>
                <p>
                  Compose this role from other roles -- everyone with this role also gets everything the added roles grant.
                  {includedRoleIds.length ? ` ${effectivePermissionCount} total permission${effectivePermissionCount === 1 ? "" : "s"}.` : ""}
                </p>
              </div>
            </button>

            {rolesExpanded && (
              includableRoles.length ? (
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
                          {normalizedSearch ? "No roles match your search." : "All roles have been added."}
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
                <small>No other roles exist yet to add.</small>
              )
            )}
          </section>

          </fieldset>

          <div className="role-editor-actions">
            <Link to="/settings/iam?section=roles" className="secondary-button">
              {isLocked ? "Back" : "Cancel"}
            </Link>
            {!isLocked && (
              <button
                type="submit"
                className="primary-button small"
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? "Saving..." : isEditing ? "Save role" : "Create role"}
              </button>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
