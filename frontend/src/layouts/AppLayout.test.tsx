import { render, screen, waitFor } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppLayout } from "./AppLayout";
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

function renderLayout() {
  return render(
    <TestProviders>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="*" element={<div>page content</div>} />
        </Route>
      </Routes>
    </TestProviders>,
  );
}

describe("AppLayout navigation gating", () => {
  it("shows the Dashboard nav link for a user with analytics.dashboard", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile(["analytics.dashboard"]));
    renderLayout();

    await waitFor(() => expect(screen.getByText("Dashboard")).toBeInTheDocument());
  });

  it("hides the Dashboard nav link for a user without analytics.dashboard", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile(["projects.read"]));
    renderLayout();

    await waitFor(() => expect(screen.getByText("Projects")).toBeInTheDocument());
    expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
  });

  it("always shows Settings and Projects regardless of permissions", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile([]));
    renderLayout();

    await waitFor(() => expect(screen.getByText("Projects")).toBeInTheDocument());
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });
});
