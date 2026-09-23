import { apiClient } from "./client";

import type {
  AcceptInvitationRequest,
  InvitationPreview,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
} from "../types/auth";

export async function login(
  request: LoginRequest,
): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>(
    "/api/v1/auth/login",
    {
      email: request.email,
      password: request.password,
    },
  );

  return response.data;
}

export async function register(
  request: RegisterRequest,
): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>(
    "/api/v1/auth/register",
    request,
  );

  return response.data;
}

export async function getInvitationPreview(token: string): Promise<InvitationPreview> {
  const response = await apiClient.get<InvitationPreview>(
    `/api/v1/auth/invitations/${encodeURIComponent(token)}`,
  );
  return response.data;
}

export async function acceptInvitation(
  token: string,
  request: AcceptInvitationRequest,
): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>(
    `/api/v1/auth/invitations/${encodeURIComponent(token)}/accept`,
    request,
  );
  return response.data;
}

export async function forgotPassword(email: string): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>(
    "/api/v1/auth/forgot-password",
    { email },
  );
  return response.data;
}

export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>(
    "/api/v1/auth/reset-password",
    { token, new_password: newPassword },
  );
  return response.data;
}

export async function verifyEmail(token: string): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>(
    "/api/v1/auth/verify-email",
    { token },
  );
  return response.data;
}

export async function resendVerification(email: string): Promise<{ message: string }> {
  const response = await apiClient.post<{ message: string }>(
    "/api/v1/auth/resend-verification",
    { email },
  );
  return response.data;
}
