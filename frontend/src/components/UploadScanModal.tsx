import { useEffect, useState } from "react";

import { Alert, Form, Modal, Progress, Select } from "antd";

import type { ScanType } from "../types/scan";

const SCAN_TYPES: ScanType[] = [
  "SAST",
  "SCA",
  "Secrets",
  "Container Security",
  "IaC",
  "DAST",
];

interface UploadScanFormValues {
  scan_type: ScanType;
}

interface UploadScanModalProps {
  isOpen: boolean;
  projectName: string;
  isSubmitting: boolean;
  progress: number;
  error?: string;
  onClose: () => void;
  onSubmit: (scanType: ScanType, file: File) => Promise<void>;
}

export function UploadScanModal({
  isOpen,
  projectName,
  isSubmitting,
  progress,
  error,
  onClose,
  onSubmit,
}: UploadScanModalProps) {
  const [form] = Form.useForm<UploadScanFormValues>();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");

  useEffect(() => {
    if (!isOpen) return;
    form.setFieldsValue({ scan_type: "SAST" });
    setFile(null);
    setFileError("");
  }, [form, isOpen]);

  async function handleFinish(values: UploadScanFormValues): Promise<void> {
    if (!file) {
      setFileError("Select a SARIF file to upload.");
      return;
    }
    setFileError("");
    await onSubmit(values.scan_type, file);
  }

  return (
    <Modal
      open={isOpen}
      title={`Upload scan result — ${projectName}`}
      onCancel={onClose}
      onOk={() => form.submit()}
      okText={isSubmitting ? "Uploading..." : "Upload scan"}
      confirmLoading={isSubmitting}
      cancelButtonProps={{ disabled: isSubmitting }}
      destroyOnHidden
    >
      {error && (
        <Alert
          type="error"
          message={error}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Form form={form} layout="vertical" onFinish={handleFinish}>
        <Form.Item
          label="Scan type"
          name="scan_type"
          rules={[{ required: true, message: "Scan type is required." }]}
        >
          <Select disabled={isSubmitting} options={SCAN_TYPES.map((type) => ({ label: type, value: type }))} />
        </Form.Item>

        <Form.Item label="SARIF file" required>
          <input
            type="file"
            className="scan-upload-file-input"
            accept=".sarif,.sarif.json,.json,application/sarif+json,application/json"
            disabled={isSubmitting}
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setFileError("");
            }}
          />
          <div className="scan-upload-file-hint">
            {file ? file.name : "Only SARIF (.sarif) results files from your scanner are accepted."}
          </div>
          {fileError && <div className="scan-upload-file-error">{fileError}</div>}
        </Form.Item>

        {isSubmitting && (
          <Form.Item>
            <Progress percent={progress} status="active" />
            <div className="scan-upload-progress-label">
              {progress >= 100 ? "Processing scan results..." : "Uploading..."}
            </div>
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}
