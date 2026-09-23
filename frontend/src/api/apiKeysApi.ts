import type { ApiKey, CreatedApiKey } from "../types/apiKey";
import { apiClient } from "./client";

export async function getApiKeys(): Promise<ApiKey[]> {
  const response = await apiClient.get<ApiKey[]>("/api/v1/api-keys");
  return response.data;
}

export async function createApiKey(name: string): Promise<CreatedApiKey> {
  const response = await apiClient.post<CreatedApiKey>("/api/v1/api-keys", { name });
  return response.data;
}

export async function regenerateApiKey(keyId: number): Promise<CreatedApiKey> {
  const response = await apiClient.post<CreatedApiKey>(`/api/v1/api-keys/${keyId}/regenerate`);
  return response.data;
}

export async function deleteApiKey(keyId: number): Promise<void> {
  await apiClient.delete(`/api/v1/api-keys/${keyId}`);
}
