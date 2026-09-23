export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface AuthUser {
  email: string;
}

export interface RegisterRequest {
  organization_name: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
}

export interface InvitationPreview {
  organization_name: string;
  email: string;
}

export interface AcceptInvitationRequest {
  first_name: string;
  last_name: string;
  password: string;
}
