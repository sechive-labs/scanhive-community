import {
  MoreVertical,
  Plus,
  RefreshCw,
  Upload,
} from "lucide-react";

import {
  App,
  Button,
  Dropdown,
  Table,
  Tooltip,
} from "antd";
import type { SortOrder } from "antd/es/table/interface";

import { useEffect, useState } from "react";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { useNavigate } from "react-router-dom";

import {
  createProject,
  deleteProject,
  exportProjectReport,
  getProjects,
  updateProject,
  uploadScan,
} from "../api/projectsApi";
import { getProfile } from "../api/iamApi";

import { DeleteProjectModal } from "../components/DeleteProjectModal";
import { LoadingState } from "../components/LoadingState";
import { ProjectModal } from "../components/ProjectModal";
import { UploadScanModal } from "../components/UploadScanModal";

import type {
  Project,
  ProjectCreateRequest,
  ProjectSummary,
} from "../types/project";
import type { ScanType } from "../types/scan";
import {
  formatLocalDateTime,
  formatRelativeTime,
} from "../utils/date";
import { getApiErrorMessage } from "../utils/apiError";

function getTotalVulnerabilities(
  project: ProjectSummary,
): number {
  return (
    project.critical +
    project.high +
    project.medium +
    project.low +
    project.info
  );
}

function getErrorMessage(error: unknown): string {
  return getApiErrorMessage(error);
}

export function ProjectsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const [isProjectModalOpen, setProjectModalOpen] =
    useState(false);

  const [editingProject, setEditingProject] =
    useState<Project | null>(null);

  const [deletingProject, setDeletingProject] =
    useState<Project | null>(null);

  const [exportingProject, setExportingProject] =
    useState<string | null>(null);

  const [uploadingProject, setUploadingProject] =
    useState<ProjectSummary | null>(null);

  const [uploadError, setUploadError] =
    useState("");

  const [uploadProgress, setUploadProgress] =
    useState(0);

  const [actionError, setActionError] =
    useState("");

  const [searchQuery, setSearchQuery] =
    useState("");

  const [scannerFilter, setScannerFilter] =
    useState("");

  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setNow(Date.now());
    }, 30_000);

    return () => window.clearInterval(intervalId);
  }, []);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: getProjects,
    // Keeps scan counts/vulnerability totals current as background scans
    // finish, without a visible reload -- React Query only shows the
    // loading state on the first fetch, so this refresh is silent.
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const profileQuery = useQuery({ queryKey: ["iam-profile"], queryFn: getProfile });
  const canCreateProject = profileQuery.data?.effective_permissions.includes("projects.create") ?? false;
  const currentUserId = profileQuery.data?.id;
  const effectivePermissions = profileQuery.data?.effective_permissions ?? [];

  function hasProjectAccess(
    project: ProjectSummary,
    ...permissions: string[]
  ): boolean {
    if (currentUserId !== undefined && project.owner_id === currentUserId) {
      return true;
    }
    return permissions.some((permission) => effectivePermissions.includes(permission));
  }

  const saveMutation = useMutation({
    mutationFn: async (
      request: ProjectCreateRequest,
    ) => {
      if (editingProject) {
        return updateProject(
          editingProject.id,
          request,
        );
      }

      return createProject(request);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["projects"],
      });

      setProjectModalOpen(false);
      setEditingProject(null);
      setActionError("");
    },
    onError: (error) => {
      setActionError(getErrorMessage(error));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["projects"],
      });

      setDeletingProject(null);
      setActionError("");
    },
    onError: (error) => {
      setActionError(getErrorMessage(error));
    },
  });

  const uploadMutation = useMutation({
    mutationFn: ({ scanType, file }: { scanType: ScanType; file: File }) =>
      uploadScan(uploadingProject!.id, scanType, file, setUploadProgress),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      setUploadingProject(null);
      setUploadError("");
      setUploadProgress(0);
      message.success(`${result.filename} uploaded -- ${result.findings} finding${result.findings === 1 ? "" : "s"} found.`);
    },
    onError: (error) => {
      setUploadProgress(0);
      setUploadError(getErrorMessage(error));
    },
  });

  function openUploadModal(project: ProjectSummary): void {
    setUploadError("");
    setUploadProgress(0);
    setUploadingProject(project);
  }

  function openCreateModal(): void {
    if (!canCreateProject) return;
    setEditingProject(null);
    setActionError("");
    setProjectModalOpen(true);
  }

  function closeProjectModal(): void {
    if (saveMutation.isPending) {
      return;
    }

    setProjectModalOpen(false);
    setEditingProject(null);
    setActionError("");
  }

  async function handleSaveProject(
    request: ProjectCreateRequest,
  ): Promise<void> {
    setActionError("");
    await saveMutation.mutateAsync(request);
  }

  async function handleDeleteProject(): Promise<void> {
    if (!deletingProject) {
      return;
    }

    setActionError("");

    await deleteMutation.mutateAsync(
      deletingProject.id,
    );
  }

  async function downloadProjectReport(
    project: ProjectSummary,
    format: "pdf" | "csv",
  ): Promise<void> {
    const exportKey = `${project.id}:${format}`;
    setExportingProject(exportKey);

    try {
      const blob = await exportProjectReport(
        project.id,
        format,
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${project.name.replaceAll(" ", "_")}_security_report.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      message.success(
        `${format.toUpperCase()} report downloaded.`,
      );
    } catch {
      message.error(
        "Unable to generate the project report.",
      );
    } finally {
      setExportingProject(null);
    }
  }

  const projects = projectsQuery.data ?? [];
  const normalizedSearchQuery = searchQuery
    .trim()
    .toLowerCase();
  const scannerOptions = Array.from(
    new Set(projects.flatMap((project) => project.scanners ?? [])),
  ).sort();
  const filteredCount = projects.filter((project) => {
    const matchesName = project.name
      .toLowerCase()
      .includes(normalizedSearchQuery);
    const matchesScanner =
      !scannerFilter || project.scanners?.includes(scannerFilter);
    return matchesName && Boolean(matchesScanner);
  }).length;

  const columns = [
    {
      title: "Project name",
      dataIndex: "name",
      key: "name",
      sorter: (a: ProjectSummary, b: ProjectSummary) =>
        a.name.localeCompare(b.name),
      filteredValue: searchQuery ? [searchQuery] : null,
      filterDropdown: () => (
        <div className="table-filter-menu">
          <input
            type="search"
            value={searchQuery}
            placeholder="Search projects"
            autoFocus
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </div>
      ),
      onFilter: (value: unknown, record: ProjectSummary) =>
        record.name.toLowerCase().includes(String(value).toLowerCase()),
      render: (name: string, project: ProjectSummary) => (
        <button
          type="button"
          className="project-name-cell"
          onClick={() => navigate(`/projects/${project.id}`)}
        >
          <strong>{name}</strong>
        </button>
      ),
    },
    {
      title: "Last scan",
      dataIndex: "last_scan",
      key: "last_scan",
      sorter: (
        a: ProjectSummary,
        b: ProjectSummary,
        sortOrder?: SortOrder,
      ) => {
        if (!a.last_scan && !b.last_scan) return 0;
        if (!a.last_scan) return sortOrder === "descend" ? -1 : 1;
        if (!b.last_scan) return sortOrder === "descend" ? 1 : -1;
        return (
          new Date(a.last_scan).getTime() -
          new Date(b.last_scan).getTime()
        );
      },
      render: (_: unknown, project: ProjectSummary) => (
        <span
          className="project-cell muted"
          title={formatLocalDateTime(project.last_scan)}
        >
          {formatRelativeTime(project.last_scan, now)}
        </span>
      ),
    },
    {
      title: "Scanners",
      dataIndex: "scanners",
      key: "scanners",
      filteredValue: scannerFilter ? [scannerFilter] : null,
      filterMultiple: false,
      filters: scannerOptions.map((scanner) => ({
        text: scanner,
        value: scanner,
      })),
      onFilter: (value: unknown, record: ProjectSummary) =>
        Boolean(record.scanners?.includes(String(value))),
      render: (scanners: string[] | null) => (
        <div className="scanner-list">
          {scanners?.length ? (
            scanners.map((scanner) => (
              <span className="scanner-badge" key={scanner}>
                {scanner}
              </span>
            ))
          ) : (
            <span className="scanner-badge">No scanners</span>
          )}
        </div>
      ),
    },
    {
      title: "Total vulnerabilities",
      key: "vulnerabilities",
      sorter: (a: ProjectSummary, b: ProjectSummary) =>
        getTotalVulnerabilities(a) - getTotalVulnerabilities(b),
      render: (_: unknown, project: ProjectSummary) => (
        <div
          className="vulnerability-summary"
          tabIndex={0}
          aria-label={`Total vulnerabilities ${getTotalVulnerabilities(project)}. Critical ${project.critical}, high ${project.high}, medium ${project.medium}, low ${project.low}, info ${project.info}.`}
        >
          <span className="vulnerability-bar" aria-hidden="true">
            <i className="critical" />
            <i className="high" />
            <i className="medium" />
            <i className="low" />
            <i className="info" />
          </span>
          <strong>{getTotalVulnerabilities(project)}</strong>
          <span className="vulnerability-tooltip" role="tooltip">
            C:{project.critical} H:{project.high}{" "}
            M:{project.medium} L:{project.low} I:{project.info}
          </span>
        </div>
      ),
    },
    {
      title: "",
      key: "upload",
      width: 56,
      render: (_: unknown, project: ProjectSummary) => {
        const canUpload = hasProjectAccess(project, "scans.upload");
        return (
          <Tooltip title={canUpload ? "Upload scan result" : "You don't have permission to upload scans for this project."}>
            <Button
              type="text"
              size="small"
              className="project-upload-button"
              icon={<Upload size={15} />}
              aria-label={`Upload scan for ${project.name}`}
              disabled={!canUpload}
              onClick={() => openUploadModal(project)}
            />
          </Tooltip>
        );
      },
    },
    {
      title: "",
      key: "actions",
      width: 56,
      render: (_: unknown, project: ProjectSummary) => {
        // The Settings page has two independently-gated tabs (General needs
        // projects.edit, Access needs projects.settings) -- the menu entry
        // itself opens if the user qualifies for either one.
        const canOpenSettings = hasProjectAccess(
          project,
          "projects.settings", "projects.edit",
        );
        const canExport = hasProjectAccess(project, "projects.read");
        const canDelete = hasProjectAccess(project, "projects.delete");

        function menuLabel(label: string, allowed: boolean, reason: string) {
          if (allowed) return label;
          return (
            <Tooltip title={reason} placement="left">
              <span>{label}</span>
            </Tooltip>
          );
        }

        return (
          <div className="project-menu-wrapper">
            <Dropdown
              trigger={["click"]}
              placement="bottomRight"
              menu={{
                items: [
                  {
                    key: "settings",
                    label: menuLabel("Project settings", canOpenSettings, "You don't have permission to manage this project's settings."),
                    disabled: !canOpenSettings,
                  },
                  { type: "divider" },
                  {
                    key: "pdf",
                    label: menuLabel("Export PDF", canExport, "You don't have permission to export this project."),
                    disabled: exportingProject !== null || !canExport,
                  },
                  {
                    key: "csv",
                    label: menuLabel("Export CSV", canExport, "You don't have permission to export this project."),
                    disabled: exportingProject !== null || !canExport,
                  },
                  { type: "divider" },
                  {
                    key: "delete",
                    label: menuLabel("Delete project", canDelete, "You don't have permission to delete this project."),
                    danger: true,
                    disabled: !canDelete,
                  },
                ],
                onClick: ({ key }) => {
                  if (key === "settings") {
                    navigate(
                      `/projects/${project.id}/settings`,
                    );
                  } else if (
                    key === "pdf" ||
                    key === "csv"
                  ) {
                    void downloadProjectReport(
                      project,
                      key,
                    );
                  } else if (key === "delete") {
                    setActionError("");
                    setDeletingProject(project);
                  }
                },
              }}
            >
              <Button
                type="text"
                size="small"
                className="project-actions-button"
                aria-label={`Actions for ${project.name}`}
                loading={
                  exportingProject?.startsWith(
                    `${project.id}:`,
                  ) ?? false
                }
                icon={<MoreVertical size={18} />}
              />
            </Dropdown>
          </div>
        );
      },
    },
  ];

  return (
    <div className="page-container projects-page">
      <div className="page-heading">
        <div>
          <h1>Projects</h1>
        </div>

        <span className="permission-tooltip-wrapper">
          <button
            type="button"
            className="primary-button small"
            disabled={!canCreateProject}
            onClick={openCreateModal}
          >
            <Plus size={18} />
            Create project
          </button>
          {!canCreateProject && (
            <span className="permission-tooltip" role="tooltip">
              You don&apos;t have permission to create a project.
            </span>
          )}
        </span>
      </div>

      {actionError && (
        <div className="alert-error page-alert">
          {actionError}
        </div>
      )}

      {projectsQuery.isLoading && (
        <LoadingState><p>Loading projects...</p></LoadingState>
      )}

      {projectsQuery.isError && (
        <div className="empty-state">
          <h2>Unable to load projects</h2>

          <p>
            {getErrorMessage(projectsQuery.error)}
          </p>

          <button
            type="button"
            className="secondary-button"
            onClick={() =>
              projectsQuery.refetch()
            }
          >
            <RefreshCw size={17} />
            Try again
          </button>
        </div>
      )}

      {!projectsQuery.isLoading &&
        !projectsQuery.isError &&
        projects.length === 0 && (
          <div className="empty-state">
            <h2>No projects yet</h2>

            <p>
              Create your first project to begin
              importing SARIF security reports.
            </p>

            <span className="permission-tooltip-wrapper">
              <button
                type="button"
                className="primary-button small"
                disabled={!canCreateProject}
                onClick={openCreateModal}
              >
                <Plus size={18} />
                Create first project
              </button>
              {!canCreateProject && (
                <span className="permission-tooltip" role="tooltip">
                  You don&apos;t have permission to create a project.
                </span>
              )}
            </span>
          </div>
        )}

      {!projectsQuery.isLoading &&
        !projectsQuery.isError &&
        projects.length > 0 && (
          <>
            <div className="projects-summary">
              <span>
                {filteredCount}{" "}
                {filteredCount === 1
                  ? "project"
                  : "projects"}
              </span>
            </div>

            <Table<ProjectSummary>
              rowKey="id"
              size="small"
              columns={columns}
              dataSource={projects}
              pagination={false}
              sortDirections={["ascend", "descend"]}
              locale={{ emptyText: "No projects match the selected filters." }}
              onChange={(_pagination, filters) => {
                const nextScanner = filters.scanners;
                setScannerFilter(
                  Array.isArray(nextScanner) && nextScanner.length
                    ? String(nextScanner[0])
                    : "",
                );
              }}
            />
          </>
        )}

      <ProjectModal
        isOpen={isProjectModalOpen}
        project={editingProject}
        isSubmitting={saveMutation.isPending}
        onClose={closeProjectModal}
        onSubmit={handleSaveProject}
      />

      <DeleteProjectModal
        project={deletingProject}
        isDeleting={deleteMutation.isPending}
        onClose={() => {
          if (!deleteMutation.isPending) {
            setDeletingProject(null);
            setActionError("");
          }
        }}
        onConfirm={handleDeleteProject}
      />

      <UploadScanModal
        isOpen={uploadingProject !== null}
        projectName={uploadingProject?.name ?? ""}
        isSubmitting={uploadMutation.isPending}
        progress={uploadProgress}
        error={uploadError}
        onClose={() => {
          if (!uploadMutation.isPending) {
            setUploadingProject(null);
            setUploadError("");
            setUploadProgress(0);
          }
        }}
        onSubmit={async (scanType, file) => {
          await uploadMutation.mutateAsync({ scanType, file });
        }}
      />
    </div>
  );
}
