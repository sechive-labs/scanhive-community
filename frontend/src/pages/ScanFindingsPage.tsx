import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import {
  Link,
  useNavigate,
  useParams,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Table } from "antd";

import { getScanFindings } from "../api/findingsApi";
import { getProjectScans } from "../api/projectsApi";
import { LoadingState } from "../components/LoadingState";
import type { Finding } from "../types/finding";
import { isUuid } from "../utils/uuid";

const SEVERITY_OPTIONS = [
  "critical",
  "high",
  "medium",
  "low",
  "info",
];
const RESULT_STATUS_OPTIONS = ["New", "Recurrent"];
const TRIAGE_STATUS_OPTIONS = [
  "To Verify",
  "False Positive",
  "Not Exploitable",
  "Confirmed",
  "Fixed",
];

export function ScanFindingsPage() {
  const { projectId, scanId } = useParams();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [severity, setSeverity] = useState("");
  const [resultStatus, setResultStatus] = useState("");
  const [triageStatus, setTriageStatus] = useState("");
  const isValid = isUuid(projectId) && isUuid(scanId);

  const findingsQuery = useQuery({
    queryKey: [
      "scan-findings",
      projectId,
      scanId,
      page,
      pageSize,
      severity,
      resultStatus,
      triageStatus,
    ],
    queryFn: () =>
      getScanFindings(
        projectId!,
        scanId!,
        page,
        pageSize,
        severity,
        resultStatus,
        triageStatus,
      ),
    enabled: isValid,
  });

  const scansQuery = useQuery({
    queryKey: ["project-scans", projectId],
    queryFn: () => getProjectScans(projectId!),
    enabled: isValid,
  });

  const scan = scansQuery.data?.find(
    (item) => item.id === scanId,
  );

  const columns = [
    {
      title: "Title",
      key: "result",
      width: 240,
      render: (_: unknown, finding: Finding) => (
        <div className="finding-title">
          <strong>{finding.title}</strong>
          <span>{finding.rule_id}</span>
        </div>
      ),
    },
    {
      title: "Severity",
      dataIndex: "severity",
      key: "severity",
      width: 110,
      filteredValue: severity ? [severity] : null,
      filterMultiple: false,
      filters: SEVERITY_OPTIONS.map((option) => ({
        text: option.charAt(0).toUpperCase() + option.slice(1),
        value: option,
      })),
      render: (value: string) => (
        <span className={`finding-severity ${value.toLowerCase()}`}>
          {value}
        </span>
      ),
    },
    {
      title: "Location",
      key: "file_path",
      width: 240,
      ellipsis: true,
      render: (_: unknown, finding: Finding) => (
        <span
          className="finding-location"
          title={`${finding.file_path || ""}${finding.line_number ? `:${finding.line_number}` : ""}`}
        >
          {finding.file_path || "—"}
          {finding.line_number ? `:${finding.line_number}` : ""}
        </span>
      ),
    },
    {
      title: "Description",
      dataIndex: "message",
      key: "message",
      width: 320,
      ellipsis: true,
      render: (value: string) => (
        <span className="finding-message" title={value}>
          {value || "—"}
        </span>
      ),
    },
    {
      title: "Status",
      dataIndex: "result_status",
      key: "result_status",
      width: 110,
      filteredValue: resultStatus ? [resultStatus] : null,
      filterMultiple: false,
      filters: RESULT_STATUS_OPTIONS.map((option) => ({
        text: option,
        value: option,
      })),
      render: (value: string) => (
        <span className={`result-status ${value.toLowerCase()}`}>
          {value}
        </span>
      ),
    },
    {
      title: "Triage Status",
      dataIndex: "triage_status",
      key: "triage_status",
      width: 150,
      filteredValue: triageStatus ? [triageStatus] : null,
      filterMultiple: false,
      filters: TRIAGE_STATUS_OPTIONS.map((option) => ({
        text: option,
        value: option,
      })),
      render: (value: string) => (
        <span className={`triage-status ${value.toLowerCase().replaceAll(" ", "-")}`}>
          {value}
        </span>
      ),
    },
  ];

  return (
    <div className="page-container scan-findings-page">
      <Link
        to={`/projects/${projectId}/scans`}
        className="back-link"
      >
        <ArrowLeft size={17} />
        Back to scan history
      </Link>

      <div className="page-heading findings-heading">
        <div>
          <h1>{scan ? `${scan.scan_type} Results` : "Scan Results"}</h1>
        </div>
      </div>

      {findingsQuery.isLoading && (
        <LoadingState><p>Loading results...</p></LoadingState>
      )}

      {findingsQuery.isError && (
        <div className="alert-error">Unable to load results.</div>
      )}

      {findingsQuery.data && (
        <>
          <div className="projects-summary">
            {findingsQuery.data.total.toLocaleString()} results
          </div>

          <Table<Finding>
            rowKey="id"
            size="small"
            tableLayout="fixed"
            columns={columns}
            dataSource={findingsQuery.data.items}
            scroll={{ x: 1170 }}
            locale={{ emptyText: "No results match the selected filters." }}
            onRow={(finding) => ({
              onClick: () =>
                navigate(
                  `/projects/${projectId}/scans/${scanId}/results/${finding.id}`,
                ),
            })}
            pagination={{
              current: page,
              pageSize,
              total: findingsQuery.data.total,
              showSizeChanger: true,
              pageSizeOptions: [25, 50, 100],
            }}
            onChange={(paginationConfig, filters, _sorter, extra) => {
              if (extra.action === "filter") {
                const nextSeverity = filters.severity;
                setSeverity(
                  Array.isArray(nextSeverity) && nextSeverity.length
                    ? String(nextSeverity[0])
                    : "",
                );

                const nextResultStatus = filters.result_status;
                setResultStatus(
                  Array.isArray(nextResultStatus) && nextResultStatus.length
                    ? String(nextResultStatus[0])
                    : "",
                );

                const nextTriageStatus = filters.triage_status;
                setTriageStatus(
                  Array.isArray(nextTriageStatus) && nextTriageStatus.length
                    ? String(nextTriageStatus[0])
                    : "",
                );

                setPage(1);
                return;
              }

              if (extra.action === "paginate") {
                const nextPage = paginationConfig.current ?? 1;
                const nextPageSize = paginationConfig.pageSize ?? pageSize;

                if (nextPageSize !== pageSize) {
                  setPageSize(nextPageSize);
                  setPage(1);
                } else {
                  setPage(nextPage);
                }
              }
            }}
          />
        </>
      )}
    </div>
  );
}
