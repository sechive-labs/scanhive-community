import { useQuery } from "@tanstack/react-query";

import { getProfile } from "../api/iamApi";

/**
 * Reads the current user's effective permissions (own roles + group roles)
 * to drive UI-side enable/disable. This is a UX convenience only -- the
 * backend re-checks every permission on every request and is the real
 * authorization boundary.
 *
 * Shares the "iam-profile" query cache with AppLayout and IamSettingsPage,
 * so calling this in multiple components does not trigger extra requests.
 */
export function usePermissions() {
  const profileQuery = useQuery({ queryKey: ["iam-profile"], queryFn: getProfile });
  const effectivePermissions = profileQuery.data?.effective_permissions ?? [];

  function hasPermission(permission: string): boolean {
    return effectivePermissions.includes(permission);
  }

  function hasAnyPermission(...permissions: string[]): boolean {
    return permissions.some((permission) => effectivePermissions.includes(permission));
  }

  function hasAnyIamPermission(): boolean {
    return effectivePermissions.some((permission) => permission.startsWith("iam."));
  }

  return {
    effectivePermissions,
    hasPermission,
    hasAnyPermission,
    hasAnyIamPermission,
    isLoading: profileQuery.isLoading,
    profile: profileQuery.data,
  };
}
