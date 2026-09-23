import { useEffect } from "react";

import { Form, Input, Modal } from "antd";

import type {
  Project,
  ProjectCreateRequest,
} from "../types/project";

interface ProjectModalProps {
  isOpen: boolean;
  project?: Project | null;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (
    request: ProjectCreateRequest,
  ) => Promise<void>;
}

export function ProjectModal({
  isOpen,
  project,
  isSubmitting,
  onClose,
  onSubmit,
}: ProjectModalProps) {
  const [form] = Form.useForm<ProjectCreateRequest>();

  const isEditing = Boolean(project);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    form.setFieldsValue({
      name: project?.name ?? "",
      description: project?.description ?? "",
    });
  }, [form, isOpen, project]);

  async function handleFinish(
    values: ProjectCreateRequest,
  ): Promise<void> {
    await onSubmit({
      name: values.name.trim(),
      description: (values.description ?? "").trim(),
    });
  }

  return (
    <Modal
      open={isOpen}
      title={isEditing ? "Edit project" : "Create project"}
      onCancel={onClose}
      confirmLoading={isSubmitting}
      okText={
        isSubmitting
          ? "Saving..."
          : isEditing
            ? "Save changes"
            : "Create project"
      }
      cancelButtonProps={{ disabled: isSubmitting }}
      onOk={() => form.submit()}
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
      >
        <Form.Item
          label="Project name"
          name="name"
          rules={[
            {
              required: true,
              message: "Project name is required.",
              whitespace: true,
            },
          ]}
        >
          <Input
            placeholder="Customer portal"
            maxLength={100}
            autoFocus
          />
        </Form.Item>

        <Form.Item label="Description" name="description">
          <Input.TextArea
            placeholder="Security findings and scan reports for this project."
            maxLength={500}
            rows={5}
            showCount
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
