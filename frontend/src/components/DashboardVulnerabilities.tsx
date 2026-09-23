import { useQuery } from "@tanstack/react-query";
import { App, Button, Dropdown, Select } from "antd";
import { useState } from "react";
import { Download } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { exportPortfolioVulnerabilities, getPortfolioVulnerabilities } from "../api/dashboardApi";
import type { DashboardAnalytics } from "../types/dashboard";
import { useScanHiveTheme } from "../theme/ScanHiveThemeProvider";

const SEVERITY_COLORS: Record<string, string> = { Critical: "#e11d48", High: "#f97316", Medium: "#eab308", Low: "#3b82f6", Info: "#64748b" };
const STATUS_COLORS: Record<string, string> = { New: "#4f6bed", Recurrent: "#8b5cf6" };

export function DashboardVulnerabilities({ analytics }: { analytics: DashboardAnalytics }) {
  const { message } = App.useApp();
  const { mode } = useScanHiveTheme();
  const [projectId, setProjectId] = useState("");
  const [severity, setSeverity] = useState("");
  const [triageStatus, setTriageStatus] = useState("");
  const [resultStatus, setResultStatus] = useState("");
  const [exporting, setExporting] = useState(false);
  const filters = { projectId, severity, triageStatus, resultStatus, search: "", page: 1, pageSize: 1 };
  const query = useQuery({ queryKey: ["portfolio-vulnerabilities", filters], queryFn: () => getPortfolioVulnerabilities(filters), placeholderData: (previous) => previous });
  const chartText = mode === "dark" ? "#94a3b8" : "#64748b";
  const chartGrid = mode === "dark" ? "#273449" : "#e2e8f0";
  const tooltipStyle = { color: mode === "dark" ? "#e2e8f0" : "#172033", background: mode === "dark" ? "#111827" : "#fff", border: `1px solid ${mode === "dark" ? "#334155" : "#dce2ea"}`, borderRadius: "6px", fontSize: "12px" };
  const fixed = query.data?.triage.find((item) => item.name === "Fixed")?.value ?? 0;
  const toVerify = query.data?.triage.find((item) => item.name === "To Verify")?.value ?? 0;
  const priority = (query.data?.severity.find((item) => item.name === "Critical")?.value ?? 0) + (query.data?.severity.find((item) => item.name === "High")?.value ?? 0);

  function updateFilter(setter: (value: string) => void, value: string) { setter(value); }
  async function exportReport(format: "pdf" | "csv") {
    setExporting(true);
    try {
      const blob = await exportPortfolioVulnerabilities(format, filters);
      const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
      anchor.href = url; anchor.download = `ScanHive_portfolio_results.${format}`; anchor.click(); URL.revokeObjectURL(url);
      message.success(`${format.toUpperCase()} report downloaded.`);
    } catch { message.error("Unable to export the vulnerability report."); } finally { setExporting(false); }
  }

  return <section className="portfolio-vulnerabilities">
    <div className="vulnerability-toolbar">
      <Select value={severity} onChange={(value) => updateFilter(setSeverity, value)} options={[{ value: "", label: "All severities" }, ...["Critical", "High", "Medium", "Low", "Info"].map((value) => ({ value, label: value }))]} />
      <Select value={projectId} onChange={(value) => updateFilter(setProjectId, value)} options={[{ value: "", label: "All projects" }, ...analytics.filters.projects.map((project) => ({ value: project.id, label: project.name }))]} />
      <Select value={triageStatus} onChange={(value) => updateFilter(setTriageStatus, value)} options={[{ value: "", label: "All triage statuses" }, ...["To Verify", "Confirmed", "Fixed", "False Positive", "Not Exploitable"].map((value) => ({ value, label: value }))]} />
      <Select value={resultStatus} onChange={(value) => updateFilter(setResultStatus, value)} options={[{ value: "", label: "All statuses" }, { value: "New", label: "New" }, { value: "Recurrent", label: "Recurrent" }]} />
      <Dropdown menu={{ items: [{ key: "pdf", label: "Export PDF" }, { key: "csv", label: "Export CSV" }], onClick: ({ key }) => exportReport(key as "pdf" | "csv") }}><Button loading={exporting} icon={<Download size={14} />}>Export</Button></Dropdown>
    </div>
    <div className="vulnerability-kpis">
      <article><span>Total vulnerabilities</span><strong>{query.data?.total.toLocaleString() ?? "—"}</strong></article>
      <article className="priority"><span>Critical &amp; high</span><strong>{priority.toLocaleString()}</strong></article>
      <article><span>To verify</span><strong>{toVerify.toLocaleString()}</strong></article>
      <article className="fixed"><span>Fixed</span><strong>{fixed.toLocaleString()}</strong></article>
    </div>
    <div className="vulnerability-chart-grid">
      <article className="analytics-card vulnerability-chart-card"><header><div><h2>Severity distribution</h2><p>Current filtered vulnerabilities</p></div></header><div className="vulnerability-chart-body"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={query.data?.severity ?? []} dataKey="value" nameKey="name" innerRadius={54} outerRadius={78} paddingAngle={2}>{query.data?.severity.map((item) => <Cell key={item.name} fill={SEVERITY_COLORS[item.name] ?? "#64748b"} />)}</Pie><Tooltip contentStyle={tooltipStyle} /></PieChart></ResponsiveContainer></div><div className="vulnerability-chart-legend">{query.data?.severity.map((item) => <span key={item.name}><i style={{ background: SEVERITY_COLORS[item.name] }} />{item.name} <strong>{item.value}</strong></span>)}</div></article>
      <article className="analytics-card vulnerability-chart-card"><header><div><h2>Triage status</h2><p>Validation and remediation progress</p></div></header><div className="vulnerability-chart-body"><ResponsiveContainer width="100%" height="100%"><BarChart data={query.data?.triage ?? []} margin={{ top: 8, right: 8, left: -20, bottom: 30 }}><CartesianGrid stroke={chartGrid} strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" stroke={chartText} tickLine={false} axisLine={false} interval={0} angle={-18} textAnchor="end" fontSize={10} /><YAxis stroke={chartText} tickLine={false} axisLine={false} allowDecimals={false} /><Tooltip contentStyle={tooltipStyle} /><Bar dataKey="value" name="Vulnerabilities" fill="#4f6bed" radius={[3, 3, 0, 0]} maxBarSize={38} /></BarChart></ResponsiveContainer></div></article>
      <article className="analytics-card vulnerability-chart-card vulnerability-status-card"><header><div><h2>Finding status</h2><p>New and recurrent vulnerabilities</p></div></header><div className="vulnerability-chart-body"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={query.data?.status ?? []} dataKey="value" nameKey="name" innerRadius={52} outerRadius={76}>{query.data?.status.map((item) => <Cell key={item.name} fill={STATUS_COLORS[item.name] ?? "#64748b"} />)}</Pie><Tooltip contentStyle={tooltipStyle} /></PieChart></ResponsiveContainer></div><div className="vulnerability-chart-legend centered">{query.data?.status.map((item) => <span key={item.name}><i style={{ background: STATUS_COLORS[item.name] }} />{item.name} <strong>{item.value}</strong></span>)}</div></article>
    </div>
  </section>;
}
