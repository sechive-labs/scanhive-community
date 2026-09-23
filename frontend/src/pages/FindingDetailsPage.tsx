import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  Pencil,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  getFindingDetails,
  updateFindingTriage,
} from "../api/findingsApi";
import { LoadingState } from "../components/LoadingState";
import type { TriageStatus } from "../types/finding";
import { isUuid } from "../utils/uuid";
import { formatLocalDateTime } from "../utils/date";

const TRIAGE_STATUSES: TriageStatus[] = [
  "To Verify",
  "False Positive",
  "Not Exploitable",
  "Confirmed",
  "Fixed",
];

export function FindingDetailsPage() {
  const { projectId, scanId, findingId } = useParams();
  const parsedFindingId = Number(findingId);
  const queryClient = useQueryClient();
  const [isEditing, setEditing] = useState(false);
  const [isHistoryExpanded, setHistoryExpanded] = useState(false);
  const [status, setStatus] = useState<TriageStatus>("To Verify");
  const [comments, setComments] = useState("");
  const isValid =
    isUuid(projectId) &&
    isUuid(scanId) &&
    Number.isInteger(parsedFindingId) &&
    parsedFindingId > 0;

  const findingQuery = useQuery({
    queryKey: ["finding", projectId, parsedFindingId],
    queryFn: () =>
      getFindingDetails(projectId!, parsedFindingId),
    enabled: isValid,
  });

  useEffect(() => {
    if (!findingQuery.data) return;
    setStatus(findingQuery.data.triage_status);
    setComments(findingQuery.data.triage_comments ?? "");
  }, [findingQuery.data]);

  const triageMutation = useMutation({
    mutationFn: () =>
      updateFindingTriage(
        projectId!,
        parsedFindingId,
        status,
        comments,
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["finding", projectId, parsedFindingId],
      });
      await queryClient.invalidateQueries({
        queryKey: ["scan-findings", projectId],
      });
      setEditing(false);
    },
  });

  const finding = findingQuery.data;

  return (
    <div className="page-container finding-details-page">
      <Link
        to={`/projects/${projectId}/scans/${scanId}/results`}
        className="back-link"
      >
        <ArrowLeft size={17} />
        Back to results
      </Link>

      {findingQuery.isLoading && (
        <LoadingState><p>Loading result...</p></LoadingState>
      )}

      {findingQuery.isError && (
        <div className="alert-error">Unable to load this result.</div>
      )}

      {finding && (
        <>
          <div className="page-heading finding-detail-heading">
            <div>
              <span className={`finding-severity ${finding.severity.toLowerCase()}`}>
                {finding.severity}
              </span>
              <h1>{finding.title}</h1>
              <p>{finding.rule_id}</p>
            </div>
            <div className="finding-detail-actions">
              {!isEditing && (
                <button
                  type="button"
                  className="primary-button small"
                  onClick={() => setEditing(true)}
                >
                  <Pencil size={16} />
                  Edit Result
                </button>
              )}
            </div>
          </div>

          {triageMutation.isError && (
            <div className="alert-error page-alert">
              Unable to save triage results.
            </div>
          )}

          <div className="finding-detail-grid">
            <section className="finding-detail-panel">
              <h2>Result details</h2>
              <dl>
                <div><dt>Scanner</dt><dd>{finding.tool}</dd></div>
                <div><dt>File</dt><dd>{finding.file_path || "—"}</dd></div>
                <div>
                  <dt>Line</dt>
                  <dd>
                    {finding.line_number == null
                      ? "—"
                      : finding.end_line && finding.end_line !== finding.line_number
                        ? `${finding.line_number}–${finding.end_line}`
                        : finding.line_number}
                  </dd>
                </div>
                {(finding.cwe || finding.owasp) && (
                  <div>
                    <dt>Classification</dt>
                    <dd>
                      {[finding.cwe, finding.owasp].filter(Boolean).join(" · ")}
                    </dd>
                  </div>
                )}
                {finding.help_uri && (
                  <div>
                    <dt>Rule docs</dt>
                    <dd>
                      <a
                        className="finding-rule-link"
                        href={finding.help_uri}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View rule documentation
                      </a>
                    </dd>
                  </div>
                )}
                <div><dt>Fingerprint</dt><dd>{finding.fingerprint || "—"}</dd></div>
                <div><dt>Status</dt><dd><span className={`result-status ${finding.result_status.toLowerCase()}`}>{finding.result_status}</span></dd></div>
              </dl>
              <h3>Description</h3>
              <p className="finding-full-message">{finding.message || "—"}</p>
              {finding.snippet && (
                <>
                  <h3>Code</h3>
                  <pre className="finding-code-snippet"><code>{finding.snippet}</code></pre>
                </>
              )}
            </section>

            <section className="finding-detail-panel triage-panel">
              <h2>Triage</h2>
              {isEditing ? (
                <form
                  onSubmit={async (event) => {
                    event.preventDefault();
                    await triageMutation.mutateAsync();
                  }}
                >
                  <p className="triage-form-hint">
                    This adds a new triage entry — earlier entries are kept as history and are never changed.
                  </p>
                  <label className="form-group">
                    <span>Status</span>
                    <select
                      className="form-input"
                      value={status}
                      onChange={(event) =>
                        setStatus(event.target.value as TriageStatus)
                      }
                    >
                      {TRIAGE_STATUSES.map((item) => (
                        <option value={item} key={item}>{item}</option>
                      ))}
                    </select>
                  </label>
                  <label className="form-group">
                    <span>Comments</span>
                    <textarea
                      className="form-input form-textarea"
                      value={comments}
                      maxLength={5000}
                      rows={7}
                      placeholder="Add triage context or remediation notes."
                      onChange={(event) => setComments(event.target.value)}
                    />
                  </label>
                  <div className="modal-actions">
                    <button
                      type="button"
                      className="secondary-button"
                      disabled={triageMutation.isPending}
                      onClick={() => {
                        setStatus(finding.triage_status);
                        setComments(finding.triage_comments ?? "");
                        setEditing(false);
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="primary-button small"
                      disabled={triageMutation.isPending}
                    >
                      {triageMutation.isPending ? "Saving..." : "Save"}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="triage-summary">
                  <span>Status</span>
                  <strong
                    className={`triage-status ${finding.triage_status
                      .toLowerCase()
                      .replaceAll(" ", "-")}`}
                  >
                    {finding.triage_status}
                  </strong>
                  <span>Triaged by</span>
                  <p>{finding.triaged_by || "Not applicable"}</p>
                  <span>Comments</span>
                  <p>{finding.triage_comments || "No comments added."}</p>
                </div>
              )}

              {finding.triage_history.length > 1 && (
                <>
                  <button
                    type="button"
                    className="triage-history-toggle"
                    onClick={() => setHistoryExpanded((expanded) => !expanded)}
                    aria-expanded={isHistoryExpanded}
                  >
                    {isHistoryExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                    Triage history ({finding.triage_history.length - 1})
                  </button>
                  {isHistoryExpanded && (
                    <ul className="triage-history">
                      {finding.triage_history.slice(1).map((entry) => (
                        <li key={entry.id}>
                          <div className="triage-history-row">
                            <strong
                              className={`triage-status ${entry.triage_status
                                .toLowerCase()
                                .replaceAll(" ", "-")}`}
                            >
                              {entry.triage_status}
                            </strong>
                            <span className="triage-history-meta">
                              {entry.triaged_by || "Unknown"} · {formatLocalDateTime(entry.triaged_at)}
                            </span>
                          </div>
                          <p>{entry.comments || "No comments added."}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
