import {
  ArrowLeft,
  BarChart3,
  Download,
  MoreVertical,
  RefreshCw,
} from "lucide-react";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Dropdown } from "antd";

import {
  Link,
  NavLink,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  lazy,
  Suspense,
  useEffect,
  useState,
} from "react";

import {
  getProjectDetails,
  getProjectScans,
  exportProjectReport,
  exportScanReport,
  deleteScan,
} from "../api/projectsApi";

import { LoadingState } from "../components/LoadingState";
import type { SeveritySummary } from "../types/project";
import {
  formatLocalDateTime,
  formatRelativeTime,
} from "../utils/date";
import { isUuid } from "../utils/uuid";

const ProjectSettings = lazy(() =>
  import("../components/ProjectSettings").then((module) => ({ default: module.ProjectSettings })),
);

const SEVERITIES: Array<keyof SeveritySummary> = [
  "critical",
  "high",
  "medium",
  "low",
  "info",
];

export function ProjectDashboardPage() {
  const { message, modal } = App.useApp();
  const queryClient = useQueryClient();
  const { projectId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [now, setNow] = useState(Date.now());
  const [exporting, setExporting] = useState<"pdf" | "csv" | null>(null);
  const [scanExporting, setScanExporting] = useState<string | null>(null);
  const [scanDeleting, setScanDeleting] = useState<string | null>(null);
  const hasValidProjectId = isUuid(projectId);
  const isScanHistory = location.pathname.endsWith("/scans");
  const isSettings = location.pathname.endsWith("/settings");

  const projectDetailsQuery = useQuery({
    queryKey: ["project-details", projectId],
    queryFn: () => getProjectDetails(projectId!),
    enabled: hasValidProjectId,
    // Background refresh so scan status/vulnerability counts stay current
    // without a visible reload -- only the first fetch shows a loading state.
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const scansQuery = useQuery({
    queryKey: ["project-scans", projectId],
    queryFn: () => getProjectScans(projectId!),
    enabled: hasValidProjectId && isScanHistory,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setNow(Date.now());
    }, 30_000);

    return () => window.clearInterval(intervalId);
  }, []);

  if (!hasValidProjectId) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <h2>Invalid project</h2>
          <Link to="/projects" className="secondary-button">
            Back to projects
          </Link>
        </div>
      </div>
    );
  }

  if (projectDetailsQuery.isLoading) {
    return (
      <div className="page-container">
        <LoadingState><p>Loading project details...</p></LoadingState>
      </div>
    );
  }

  if (projectDetailsQuery.isError) {
    return (
      <div className="page-container">
        <Link to="/projects" className="back-link">
          <ArrowLeft size={17} />
          Back to projects
        </Link>

        <div className="empty-state">
          <BarChart3 size={42} />
          <h2>Unable to load project details</h2>
          <p>Please try again.</p>
          <button
            type="button"
            className="secondary-button"
            onClick={() => projectDetailsQuery.refetch()}
          >
            <RefreshCw size={17} />
            Try again
          </button>
        </div>
      </div>
    );
  }

  const project = projectDetailsQuery.data;

  if (!project) {
    return null;
  }

  const tools = Object.entries(project.tools);
  const largestToolCount = Math.max(
    ...tools.map(([, count]) => count),
    1,
  );

  async function downloadReport(format: "pdf" | "csv", reportProjectId: string, projectName: string) {
    setExporting(format);
    try {
      const blob = await exportProjectReport(reportProjectId, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${projectName.replaceAll(" ", "_")}_security_report.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      message.success(`${format.toUpperCase()} report downloaded.`);
    } catch {
      message.error("Unable to generate the project report.");
    } finally {
      setExporting(null);
    }
  }

  async function downloadScanReport(reportProjectId: string, projectName: string, scanId: string, scanType: string, format: "pdf" | "csv") {
    setScanExporting(`${scanId}:${format}`);
    try {
      const blob = await exportScanReport(reportProjectId, scanId, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${projectName.replaceAll(" ", "_")}_${scanType.replaceAll(" ", "_")}_report.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      message.success(`${scanType} ${format.toUpperCase()} report downloaded.`);
    } catch {
      message.error("Unable to generate the scan report.");
    } finally {
      setScanExporting(null);
    }
  }

  function confirmScanDeletion(scanId: string, scanType: string, scanner: string): void {
    modal.confirm({
      title: "Delete scan?",
      content: `This will permanently delete the ${scanType} scan from ${scanner} and all of its results.`,
      okText: "Delete scan",
      okButtonProps: { danger: true },
      cancelText: "Cancel",
      centered: true,
      async onOk() {
        setScanDeleting(scanId);
        try {
          await deleteScan(scanId);
          await Promise.all([
            queryClient.invalidateQueries({ queryKey: ["project-scans", projectId] }),
            queryClient.invalidateQueries({ queryKey: ["project-details", projectId] }),
            queryClient.invalidateQueries({ queryKey: ["projects"] }),
            queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
          ]);
          message.success("Scan and associated results deleted.");
        } catch {
          message.error("Unable to delete the scan.");
          throw new Error("Scan deletion failed");
        } finally {
          setScanDeleting(null);
        }
      },
    });
  }

  return (
    <div className="page-container project-dashboard-page">
      <Link
        to="/projects"
        className="back-link"
      >
        <ArrowLeft size={17} />
        Back to projects
      </Link>

      <div className="page-heading dashboard-heading">
        <div>
          <h1 className="project-detail-title">{project.project_name}</h1>

          <p title={formatLocalDateTime(project.last_scan)}>
            Last scan: {formatRelativeTime(project.last_scan, now)}
          </p>
        </div>
        <Dropdown
          trigger={["click"]}
          menu={{
            items: [
              { key: "pdf", label: "Export PDF" },
              { key: "csv", label: "Export CSV" },
            ],
            onClick: ({ key }) => downloadReport(key as "pdf" | "csv", project.project_id, project.project_name),
          }}
        >
          <Button icon={<Download size={15} />} loading={Boolean(exporting)}>
            {exporting ? `Generating ${exporting.toUpperCase()}...` : "Export results"}
          </Button>
        </Dropdown>
      </div>

      <nav className="project-detail-tabs" aria-label="Project details">
        <NavLink end to={`/projects/${project.project_id}`}>
          Overview
        </NavLink>
        <NavLink to={`/projects/${project.project_id}/scans`}>
          Scan History
        </NavLink>
        <NavLink to={`/projects/${project.project_id}/settings`}>
          Settings
        </NavLink>
      </nav>

      {isSettings ? (
        <Suspense fallback={<LoadingState size={20} compact> Loading settings...</LoadingState>}>
          <ProjectSettings projectId={project.project_id} />
        </Suspense>
      ) : !isScanHistory ? (
        <>
      <div className="project-kpi-grid">
        <article className="project-kpi-card">
          <span>Total results</span>
          <strong>{project.total_findings.toLocaleString()}</strong>
        </article>

        <article className="project-kpi-card">
          <span>Total scans</span>
          <strong>{project.total_scans.toLocaleString()}</strong>
        </article>
      </div>

      <div className="project-detail-grid">
        <section className="project-detail-panel">
          <div className="project-panel-heading">
            <div>
              <span>Results</span>
              <h2>Severity distribution</h2>
            </div>
          </div>

          <div className="severity-grid">
            {SEVERITIES.map((severity) => (
              <article
                key={severity}
                className={`severity-card ${severity}`}
              >
                <span>{severity}</span>
                <strong>
                  {project.severity[severity].toLocaleString()}
                </strong>
              </article>
            ))}
          </div>
        </section>

        <section className="project-detail-panel">
          <div className="project-panel-heading">
            <div>
              <span>Scanners</span>
              <h2>Tool distribution</h2>
            </div>
          </div>

          {tools.length === 0 ? (
            <p className="project-panel-empty">
              No scanner data available.
            </p>
          ) : (
            <div className="tool-list">
              {tools.map(([tool, count]) => (
                <div className="tool-row" key={tool}>
                  <div className="tool-row-heading">
                    <strong>{tool}</strong>
                    <span>{count.toLocaleString()}</span>
                  </div>
                  <div className="tool-bar">
                    <span
                      style={{
                        width: `${(count / largestToolCount) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
        </>
      ) : (
        <section className="scan-history-section">
          {scansQuery.isLoading && (
            <LoadingState size={20} compact><p>Loading scans...</p></LoadingState>
          )}

          {scansQuery.isError && (
            <div className="alert-error">Unable to load scan history.</div>
          )}

          {scansQuery.data?.length === 0 && (
            <div className="scan-history-empty">No scans uploaded yet.</div>
          )}

          {scansQuery.data && scansQuery.data.length > 0 && (
            <div className="scan-history-table">
              <div className="scan-history-header">
                <span>Type</span>
                <span>Scanner</span>
                <span>File</span>
                <span>Status</span>
                <span>Results</span>
                <span>Uploaded</span>
                <span />
              </div>
              {scansQuery.data.map((scan) => (
                <div
                  className="scan-history-row"
                  key={scan.id}
                  role="button"
                  tabIndex={0}
                  onClick={() =>
                    navigate(
                      `/projects/${project.project_id}/scans/${scan.id}/results`,
                    )
                  }
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") navigate(`/projects/${project.project_id}/scans/${scan.id}/results`);
                  }}
                >
                  <strong>{scan.scan_type}</strong>
                  <span>{scan.tool}</span>
                  <span className="scan-filename" title={scan.filename}>
                    {scan.filename}
                  </span>
                  <span className={`scan-status ${scan.status.toLowerCase()}`}>
                    {scan.status}
                  </span>
                  <span>{scan.findings.toLocaleString()}</span>
                  <span title={formatLocalDateTime(scan.uploaded_at)}>
                    {formatRelativeTime(scan.uploaded_at, now)}
                  </span>
                  <Dropdown
                    trigger={["click"]}
                    menu={{
                      items: [
                        { key: "pdf", label: "Export PDF" },
                        { key: "csv", label: "Export CSV" },
                        { type: "divider" },
                        { key: "delete", label: "Delete scan", danger: true },
                      ],
                      onClick: ({ key, domEvent }) => {
                        domEvent.stopPropagation();
                        if (key === "delete") {
                          confirmScanDeletion(scan.id, scan.scan_type, scan.tool);
                        } else {
                          void downloadScanReport(project.project_id, project.project_name, scan.id, scan.scan_type, key as "pdf" | "csv");
                        }
                      },
                    }}
                  >
                    <Button
                      type="text"
                      size="small"
                      icon={<MoreVertical size={16} />}
                      loading={scanExporting?.startsWith(scan.id) || scanDeleting === scan.id}
                      aria-label={`Actions for ${scan.scan_type} scan`}
                      onClick={(event) => event.stopPropagation()}
                    />
                  </Dropdown>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
