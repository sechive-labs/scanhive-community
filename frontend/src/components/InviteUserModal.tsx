import { X } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import type { IamRole, InvitationCreateRequest } from "../types/iam";

interface InviteUserModalProps {
  isOpen: boolean;
  isSubmitting: boolean;
  error?: string;
  roles: IamRole[];
  onClose: () => void;
  onSubmit: (request: InvitationCreateRequest) => Promise<void>;
}

export function InviteUserModal({
  isOpen,
  isSubmitting,
  error,
  roles,
  onClose,
  onSubmit,
}: InviteUserModalProps) {
  const [email, setEmail] = useState("");
  const [roleIds, setRoleIds] = useState<number[]>([]);

  useEffect(() => {
    if (!isOpen) return;
    setEmail("");
    setRoleIds([]);
  }, [isOpen]);

  if (!isOpen) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim()) return;
    await onSubmit({ email: email.trim(), role_ids: roleIds });
  }

  function toggleRole(id: number) {
    setRoleIds((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current, id],
    );
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-card invite-modal-card" role="dialog" aria-modal="true">
        <div className="modal-header">
          <div><h2>Invite team member</h2></div>
          <button type="button" className="icon-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          {error && <div className="alert-error">{error}</div>}
          <label className="form-group">
            <span>Email address</span>
            <input
              className="form-input"
              type="email"
              value={email}
              placeholder="name@company.com"
              required
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <fieldset className="group-assignment-field">
            <legend>Roles</legend>
            <div>
              {roles.map((role) => (
                <label key={role.id}>
                  <input type="checkbox" checked={roleIds.includes(role.id)} onChange={() => toggleRole(role.id)} />
                  <span>{role.name}</span>
                </label>
              ))}
              {!roles.length && <small>No roles available</small>}
            </div>
          </fieldset>
          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary-button small" disabled={isSubmitting}>
              {isSubmitting ? "Sending..." : "Send invite"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
