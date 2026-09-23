import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { usePermissions } from "./usePermissions";
import { TestProviders } from "../test/testUtils";
import type { IamUser } from "../types/iam";

vi.mock("../api/iamApi", () => ({
  getProfile: vi.fn(),
}));

const { getProfile } = await import("../api/iamApi");

function mockProfile(effective_permissions: string[]): IamUser {
  return {
    id: 1,
    email: "user@example.com",
    first_name: "Test",
    last_name: "User",
    is_active: true,
    effective_permissions,
    roles: [],
    organization_id: 1,
    organization_name: "Acme",
  };
}

describe("usePermissions", () => {
  it("reports no permissions while the profile is loading", () => {
    vi.mocked(getProfile).mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => usePermissions(), { wrapper: TestProviders });
    expect(result.current.isLoading).toBe(true);
    expect(result.current.effectivePermissions).toEqual([]);
    expect(result.current.hasPermission("projects.create")).toBe(false);
  });

  it("hasPermission reflects the loaded profile's effective_permissions", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile(["projects.create", "findings.triage"]));
    const { result } = renderHook(() => usePermissions(), { wrapper: TestProviders });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.hasPermission("projects.create")).toBe(true);
    expect(result.current.hasPermission("projects.delete")).toBe(false);
  });

  it("hasAnyPermission is true when at least one of the listed permissions is granted", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile(["iam.users.update"]));
    const { result } = renderHook(() => usePermissions(), { wrapper: TestProviders });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.hasAnyPermission("iam.users.manage", "iam.users.update")).toBe(true);
    expect(result.current.hasAnyPermission("iam.users.manage", "iam.users.delete")).toBe(false);
  });

  it("hasAnyIamPermission is true for any iam.-prefixed permission, granular or broad", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile(["iam.roles.manage"]));
    const { result } = renderHook(() => usePermissions(), { wrapper: TestProviders });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.hasAnyIamPermission()).toBe(true);
  });

  it("hasAnyIamPermission is false for a user with zero iam permissions", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile(["projects.read", "scans.read"]));
    const { result } = renderHook(() => usePermissions(), { wrapper: TestProviders });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.hasAnyIamPermission()).toBe(false);
  });
});
