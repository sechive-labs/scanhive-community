export interface ApiKey {
  id: number;
  name: string;
  prefix: string;
  created_at: string;
  expires_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export interface CreatedApiKey extends ApiKey {
  key: string;
}
