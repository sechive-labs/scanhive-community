import { X } from "lucide-react";
import { useEffect, useState } from "react";

import type { IamRole, IamUser } from "../types/iam";

interface UserRolesModalProps {
  user: IamUser | null;
  roles: IamRole[];
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (roleIds: number[]) => Promise<void>;
}

export function UserRolesModal({
  user,
  roles,
  isSubmitting,
  onClose,
  onSubmit,
}: UserRolesModalProps) {
  const [selectedRoleIds, setSelectedRoleIds] = useState<number[]>([]);

  useEffect(() => {
    setSelectedRoleIds(user?.roles.map((role) => role.id) ?? []);
  }, [user]);

  if (!user) return null;

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-card iam-assignment-modal" role="dialog" aria-modal="true">
        <div className="modal-header">
          <div>
            <p className="eyebrow">User access</p>
            <h2>Assign roles to {user.first_name} {user.last_name}</h2>
          </div>
          <button type="button" className="icon-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="user-role-options">
          {roles.map((role) => (
            <label key={role.id}>
              <input
                type="checkbox"
                checked={selectedRoleIds.includes(role.id)}
                onChange={(event) =>
                  setSelectedRoleIds((current) =>
                    event.target.checked
                      ? [...current, role.id]
                      : current.filter((id) => id !== role.id),
                  )
                }
              />
              <span><strong>{role.name}</strong>{role.description}</span>
            </label>
          ))}
        </div>
        <div className="modal-actions">
          <button type="button" className="secondary-button" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="primary-button small"
            disabled={isSubmitting}
            onClick={async () => onSubmit(selectedRoleIds)}
          >
            {isSubmitting ? "Saving..." : "Save assignments"}
          </button>
        </div>
      </section>
    </div>
  );
}
