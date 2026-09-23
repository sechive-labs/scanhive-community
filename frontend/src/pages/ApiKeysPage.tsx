import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Dropdown } from "antd";
import { Check, Copy, MoreVertical, RefreshCw, X } from "lucide-react";
import { useState } from "react";

import { createApiKey, deleteApiKey, getApiKeys, regenerateApiKey } from "../api/apiKeysApi";
import type { ApiKey, CreatedApiKey } from "../types/apiKey";
import { formatLocalDateTime } from "../utils/date";
import { getApiErrorMessage } from "../utils/apiError";
import { copyToClipboard } from "../utils/clipboard";

export function ApiKeysSection() {
  const queryClient = useQueryClient();
  const { message, modal } = App.useApp();
  const [isCreateOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [createdKey, setCreatedKey] = useState<CreatedApiKey | null>(null);
  const [secretModalTitle, setSecretModalTitle] = useState("API key created");
  const [copied, setCopied] = useState(false);

  const keysQuery = useQuery({ queryKey: ["api-keys"], queryFn: getApiKeys });
  const createMutation = useMutation({
    mutationFn: () => createApiKey(name.trim()),
    onSuccess: async (key) => {
      setSecretModalTitle("API key created");
      setCreatedKey(key);
      setName("");
      setCreateOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
  const regenerateMutation = useMutation({
    mutationFn: regenerateApiKey,
    onSuccess: async (key) => {
      setSecretModalTitle("API key regenerated");
      setCreatedKey(key);
      setCopied(false);
      await queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteApiKey,
    onSuccess: async (_, keyId) => {
      queryClient.setQueryData<ApiKey[]>(["api-keys"], (keys = []) => keys.filter((key) => key.id !== keyId));
      message.success("API key deleted.");
      await queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  async function copyKey() {
    if (!createdKey) return;
    const succeeded = await copyToClipboard(createdKey.key);
    if (succeeded) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } else {
      message.error("Unable to copy automatically. Please select and copy the key manually.");
    }
  }

  return (
    <>
      {createdKey && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card api-key-created-modal" role="dialog" aria-modal="true" aria-labelledby="api-key-created-title">
            <div className="modal-header api-key-created-heading">
              <div>
                <h2 id="api-key-created-title">{secretModalTitle}</h2>
                <p>Copy this key now. It will not be displayed again.</p>
              </div>
              <button type="button" className="icon-button api-key-copy-icon" aria-label="Copy API key" title="Copy API key" onClick={copyKey}>
                {copied ? <Check size={17} /> : <Copy size={17} />}
              </button>
            </div>
            <div className="api-key-secret-row"><code>{createdKey.key}</code></div>
            <div className="api-key-validity">Valid until {formatLocalDateTime(createdKey.expires_at)}</div>
            <div className="modal-actions"><button type="button" className="primary-button small" onClick={() => { setCreatedKey(null); setCopied(false); }}>Close</button></div>
          </section>
        </div>
      )}

      <section className="iam-panel api-key-management-panel">
        <div className="iam-panel-toolbar actions-only">
          <button type="button" className="primary-button small" onClick={() => setCreateOpen(true)}>Create API key</button>
        </div>

        {keysQuery.isLoading && <div className="loading-state compact"><RefreshCw className="spin" size={19} />Loading API keys...</div>}
        {keysQuery.isError && <div className="alert-error">Unable to load API keys.</div>}
        {keysQuery.data && (
          <div className="api-key-table">
            <div className="api-key-table-header"><span>Name</span><span>Key ID</span><span>Created</span><span>Expires</span><span>Last used</span><span /></div>
            {keysQuery.data.map((key) => (
              <div className="api-key-table-row" key={key.id}>
                <strong>{key.name}</strong>
                <code>osk_{key.prefix}</code>
                <span>{formatLocalDateTime(key.created_at)}</span>
                <span>{formatLocalDateTime(key.expires_at)}</span>
                <span>{key.last_used_at ? formatLocalDateTime(key.last_used_at) : "Never"}</span>
                <Dropdown trigger={["click"]} placement="bottomRight" menu={{ items: [
                  { key: "regenerate", label: "Regenerate key" },
                  { key: "delete", label: "Delete key", danger: true },
                ], onClick: ({ key: action }) => {
                  modal.confirm({
                    title: action === "delete" ? "Delete API key?" : "Regenerate API key?",
                    content: action === "delete" ? `${key.name} will be permanently deleted.` : `The current ${key.name} key will stop working immediately.`,
                    okText: action === "delete" ? "Delete" : "Regenerate",
                    okButtonProps: { danger: true },
                    onOk: async () => action === "delete" ? deleteMutation.mutateAsync(key.id) : regenerateMutation.mutateAsync(key.id),
                  });
                } }}>
                  <Button type="text" size="small" className="api-key-actions" icon={<MoreVertical size={16} />} aria-label={`Actions for ${key.name}`} />
                </Dropdown>
              </div>
            ))}
            {keysQuery.data.length === 0 && <div className="api-key-empty">No API keys created yet.</div>}
          </div>
        )}

      </section>

      {isCreateOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card api-key-create-modal" role="dialog" aria-modal="true" aria-labelledby="create-api-key-title">
            <div className="modal-header">
              <h2 id="create-api-key-title">Create API key</h2>
              <button type="button" className="icon-button" aria-label="Close" onClick={() => { setCreateOpen(false); setName(""); }}><X size={19} /></button>
            </div>
            <form onSubmit={(event) => { event.preventDefault(); if (name.trim()) createMutation.mutate(); }}>
              <label className="form-group">
                <span>Key name</span>
                <input autoFocus className="form-input" value={name} maxLength={100} placeholder="Production CI" onChange={(event) => setName(event.target.value)} />
                <small>Use a name that identifies the pipeline or integration.</small>
              </label>
              {createMutation.isError && (
                <div className="alert-error">
                  {getApiErrorMessage(createMutation.error, "Unable to create API key.")}
                </div>
              )}
              <div className="modal-actions">
                <button type="button" className="secondary-button" onClick={() => { setCreateOpen(false); setName(""); }}>Cancel</button>
                <button type="submit" className="primary-button small" disabled={!name.trim() || createMutation.isPending}>{createMutation.isPending ? "Creating..." : "Create key"}</button>
              </div>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
