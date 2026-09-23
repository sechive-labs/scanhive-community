import { Modal } from "antd";

import type { Project } from "../types/project";

interface DeleteProjectModalProps {
  project: Project | null;
  isDeleting: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export function DeleteProjectModal({
  project,
  isDeleting,
  onClose,
  onConfirm,
}: DeleteProjectModalProps) {
  if (!project) {
    return null;
  }

  return (
    <Modal
      open
      title="Delete project?"
      onCancel={onClose}
      onOk={onConfirm}
      okType="danger"
      okText={isDeleting ? "Deleting..." : "Delete project"}
      confirmLoading={isDeleting}
      cancelButtonProps={{ disabled: isDeleting }}
    >
      <p>
        This will permanently delete{" "}
        <strong>{project.name}</strong>. Associated scans
        and findings may also be removed, depending on
        your database cascade configuration.
      </p>
    </Modal>
  );
}
