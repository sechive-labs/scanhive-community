import { X } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import type { GroupItem, GroupRequest, IamGroup } from "../types/iam";

interface GroupModalProps {
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (request: GroupRequest) => Promise<void>;
  users: GroupItem[];
  roles: GroupItem[];
  projects: GroupItem[];
  group?: IamGroup | null;
}

export function GroupModal({
  isOpen,
  isSubmitting,
  onClose,
  onSubmit,
  users,
  roles,
  projects,
  group,
}: GroupModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selections, setSelections] = useState<Record<string, Array<number | string>>>({
    user_ids: [], role_ids: [], project_ids: [],
  });
  const [memberSearch, setMemberSearch] = useState("");

  useEffect(() => {
    if (!isOpen) return;
    setName(group?.name ?? "");
    setDescription(group?.description ?? "");
    setSelections({
      user_ids: group?.users.map((item) => item.id) ?? [],
      role_ids: group?.roles.map((item) => item.id) ?? [],
      project_ids: group?.projects.map((item) => item.id) ?? [],
    });
    setMemberSearch("");
  }, [group, isOpen]);

  if (!isOpen) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) return;
    await onSubmit({
      name: name.trim(),
      description: description.trim(),
      user_ids: selections.user_ids as number[],
      role_ids: group ? selections.role_ids as number[] : [],
      project_ids: group ? selections.project_ids as string[] : [],
    });
    setName("");
    setDescription("");
    setSelections({ user_ids: [], role_ids: [], project_ids: [] });
  }

  function toggle(key: string, id: number | string) {
    setSelections((current) => ({
      ...current,
      [key]: current[key].includes(id)
        ? current[key].filter((value) => value !== id)
        : [...current[key], id],
    }));
  }

  const assignmentSections = [
    ["user_ids", "Members", users],
    ...(group ? [
      ["role_ids", "Roles", roles],
      ["project_ids", "Projects", projects],
    ] as const : []),
  ] as const;

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-card group-modal-card" role="dialog" aria-modal="true">
        <div className="modal-header">
          <div><h2>{group ? "Edit user group" : "Create user group"}</h2></div>
          <button type="button" className="icon-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <label className="form-group">
            <span>Group name</span>
            <input className="form-input" value={name} maxLength={100} required onChange={(event) => setName(event.target.value)} />
          </label>
          <div className="group-assignment-grid">
            {assignmentSections.map(([key, label, items]) => (
              <fieldset className={`group-assignment-field ${key === "user_ids" ? "members-field" : ""}`} key={key}>
                <legend>{label}</legend>
                {key === "user_ids" && (
                  <>
                    <input
                      type="search"
                      className="group-member-search"
                      value={memberSearch}
                      placeholder="Search by email..."
                      aria-label="Search members"
                      onChange={(event) => setMemberSearch(event.target.value)}
                    />
                    {!memberSearch.trim() && (
                      <small className="group-member-search-hint">Search by email to find and select users.</small>
                    )}
                  </>
                )}
                <div>
                  {items
                    .filter((item) => key !== "user_ids" || (
                      Boolean(memberSearch.trim()) &&
                      item.name.toLowerCase().includes(memberSearch.trim().toLowerCase())
                    ))
                    .map((item) => (
                    <label key={item.id}>
                      <input type="checkbox" checked={selections[key].includes(item.id)} onChange={() => toggle(key, item.id)} />
                      <span>{item.name}</span>
                    </label>
                  ))}
                  {!items.length && <small>No {label.toLowerCase()} available</small>}
                </div>
              </fieldset>
            ))}
          </div>
          <label className="form-group">
            <span>Description</span>
            <textarea className="form-input form-textarea" value={description} maxLength={500} rows={4} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary-button small" disabled={isSubmitting}>
              {isSubmitting ? "Saving..." : group ? "Save changes" : "Create group"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
