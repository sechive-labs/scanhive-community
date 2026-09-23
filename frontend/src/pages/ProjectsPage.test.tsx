import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ProjectsPage } from "./ProjectsPage";
import { TestProviders } from "../test/testUtils";
import type { IamUser } from "../types/iam";
import type { ProjectSummary } from "../types/project";

vi.mock("../api/iamApi", () => ({
  getProfile: vi.fn(),
}));

vi.mock("../api/projectsApi", () => ({
  getProjects: vi.fn(),
  createProject: vi.fn(),
  updateProject: vi.fn(),
  deleteProject: vi.fn(),
  exportProjectReport: vi.fn(),
  uploadScan: vi.fn(),
}));

const { getProfile } = await import("../api/iamApi");
const { getProjects } = await import("../api/projectsApi");

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

// owner_id intentionally does not match the mocked profile's id (1) above,
// so tests exercise the permission-based path rather than the owner-bypass
// path in ProjectsPage's hasProjectAccess().
const SAMPLE_PROJECT: ProjectSummary = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "Sample Project",
  description: null,
  owner_id: 999,
  total_vulnerabilities: 0,
  last_scan: null,
  scanners: [],
  critical: 0,
  high: 0,
  medium: 0,
  low: 0,
  info: 0,
};

describe("ProjectsPage permission gating", () => {
  it("enables the create-project button for a user with projects.create", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile(["projects.create"]));
    vi.mocked(getProjects).mockResolvedValue([SAMPLE_PROJECT]);

    render(
      <TestProviders>
        <ProjectsPage />
      </TestProviders>,
    );

    await waitFor(() => expect(screen.getByText("Sample Project")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /create project/i })).toBeEnabled();
  });

  it("disables the create-project button for a user without projects.create", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile(["projects.read"]));
    vi.mocked(getProjects).mockResolvedValue([SAMPLE_PROJECT]);

    render(
      <TestProviders>
        <ProjectsPage />
      </TestProviders>,
    );

    await waitFor(() => expect(screen.getByText("Sample Project")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /create project/i })).toBeDisabled();
  });

  it("disables the upload button for a user without scans.upload on that project", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile([]));
    vi.mocked(getProjects).mockResolvedValue([SAMPLE_PROJECT]);

    render(
      <TestProviders>
        <ProjectsPage />
      </TestProviders>,
    );

    await waitFor(() => expect(screen.getByText("Sample Project")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /upload scan for sample project/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /actions for sample project/i })).toBeInTheDocument();
  });

  it("enables the upload button when the user owns the project, regardless of role", async () => {
    vi.mocked(getProfile).mockResolvedValue(mockProfile([]));
    vi.mocked(getProjects).mockResolvedValue([{ ...SAMPLE_PROJECT, owner_id: 1 }]);

    render(
      <TestProviders>
        <ProjectsPage />
      </TestProviders>,
    );

    await waitFor(() => expect(screen.getByText("Sample Project")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /upload scan for sample project/i })).toBeEnabled();
  });
});
