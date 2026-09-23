import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getDashboardAnalytics } from "../api/dashboardApi";
import { DashboardVulnerabilities } from "../components/DashboardVulnerabilities";
import { useScanHiveTheme } from "../theme/ScanHiveThemeProvider";

const SEVERITY_COLORS: Record<string, string> = {
  Critical: "#e11d48",
  High: "#f97316",
  Medium: "#eab308",
  Low: "#3b82f6",
  Info: "#64748b",
};

export function DashboardPage() {
  const { mode } = useScanHiveTheme();
  const [projectId, setProjectId] = useState("");
  const [tool, setTool] = useState("");
  const [scanType, setScanType] = useState("");
  const [section, setSection] = useState<"overview" | "vulnerabilities">("overview");
  const filters = { projectId, tool, scanType };
  const analyticsQuery = useQuery({
    queryKey: ["dashboard-analytics", filters],
    queryFn: () => getDashboardAnalytics(filters),
    placeholderData: (previous) => previous,
  });
  const data = analyticsQuery.data;
  const hasFilters = Boolean(projectId || tool || scanType);
  const chartGrid = mode === "dark" ? "#273449" : "#e2e8f0";
  const chartText = mode === "dark" ? "#94a3b8" : "#64748b";
  const tooltipStyle = {
    color: mode === "dark" ? "#e2e8f0" : "#172033",
    background: mode === "dark" ? "#111827" : "#ffffff",
    border: `1px solid ${mode === "dark" ? "#334155" : "#dce2ea"}`,
    borderRadius: "6px",
    boxShadow: mode === "dark" ? "0 10px 28px rgba(0, 0, 0, 0.28)" : "0 10px 28px rgba(15, 23, 42, 0.12)",
    fontSize: "12px",
  };

  const posture = useMemo(() => {
    if (!data) return { priority: 0, reviewed: 0, reviewRate: 0, maximumProject: 1 };
    const priority = data.summary.critical + data.summary.high;
    return {
      priority,
      reviewed: data.summary.confirmed,
      reviewRate: data.summary.findings ? Math.round((data.summary.confirmed / data.summary.findings) * 100) : 0,
      maximumProject: Math.max(...data.by_project.map((item) => item.findings), 1),
    };
  }, [data]);

  return (
    <div className="page-container analytics-page portfolio-dashboard">
      <div className="page-heading analytics-heading">
        <div><h1>Dashboard</h1></div>
        {analyticsQuery.isFetching && <RefreshCw className="spin analytics-refresh" size={16} />}
      </div>

      {analyticsQuery.isError && <div className="alert-error">Unable to load dashboard analytics.</div>}

      <nav className="dashboard-sections" aria-label="Dashboard sections"><button type="button" className={section === "overview" ? "active" : ""} onClick={() => setSection("overview")}>Overview</button><button type="button" className={section === "vulnerabilities" ? "active" : ""} onClick={() => setSection("vulnerabilities")}>Vulnerabilities</button></nav>

      {data && section === "overview" && (
        <>
          <section className="analytics-filters dashboard-filter-bar" aria-label="Dashboard filters">
            <label><span>Project</span><select value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">All projects</option>{data.filters.projects.map((project) => <option value={project.id} key={project.id}>{project.name}</option>)}</select></label>
            <label><span>Scan type</span><select value={scanType} onChange={(event) => setScanType(event.target.value)}><option value="">All scan types</option>{data.filters.scan_types.map((type) => <option value={type} key={type}>{type}</option>)}</select></label>
            <label><span>Scanner</span><select value={tool} onChange={(event) => setTool(event.target.value)}><option value="">All scanners</option>{data.filters.tools.map((item) => <option value={item} key={item}>{item}</option>)}</select></label>
            <button type="button" className="secondary-button analytics-clear" disabled={!hasFilters} onClick={() => { setProjectId(""); setScanType(""); setTool(""); }}>Reset</button>
          </section>

          <section className="dashboard-summary-grid" aria-label="Portfolio summary">
            <article className="dashboard-primary-metric"><span>Open results</span><strong>{data.summary.findings.toLocaleString()}</strong><small>Unique across the current portfolio</small></article>
            <article className="dashboard-metric critical"><span>Critical</span><strong>{data.summary.critical.toLocaleString()}</strong><small>Requires immediate attention</small></article>
            <article className="dashboard-metric high"><span>High</span><strong>{data.summary.high.toLocaleString()}</strong><small>{posture.priority.toLocaleString()} priority results</small></article>
            <article className="dashboard-metric"><span>Confirmed</span><strong>{data.summary.confirmed.toLocaleString()}</strong><small>{posture.reviewRate}% of results confirmed</small></article>
            <article className="dashboard-metric"><span>Projects</span><strong>{data.summary.projects.toLocaleString()}</strong><small>{data.summary.scans.toLocaleString()} scans completed</small></article>
          </section>

          <section className="dashboard-main-grid">
            <article className="analytics-card dashboard-trend-panel">
              <header><div><h2>Risk activity</h2><p>New results identified during the last six months</p></div><span>6 months</span></header>
              <div className="analytics-chart dashboard-trend-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.trend} margin={{ top: 12, right: 12, left: -18, bottom: 0 }}>
                    <defs><linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#4f6bed" stopOpacity={0.34} /><stop offset="95%" stopColor="#4f6bed" stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid stroke={chartGrid} strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="label" stroke={chartText} tickLine={false} axisLine={false} />
                    <YAxis stroke={chartText} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Area type="monotone" dataKey="findings" name="New results" stroke="#4f6bed" fill="url(#riskGradient)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="analytics-card dashboard-severity-panel">
              <header><div><h2>Severity posture</h2><p>Current unique results</p></div></header>
              <div className="dashboard-severity-content">
                <div className="dashboard-donut">
                  <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.severity} dataKey="value" nameKey="name" innerRadius={54} outerRadius={76} paddingAngle={2}>{data.severity.map((entry) => <Cell key={entry.name} fill={SEVERITY_COLORS[entry.name]} />)}</Pie><Tooltip contentStyle={tooltipStyle} /></PieChart></ResponsiveContainer>
                  <div><strong>{data.summary.findings.toLocaleString()}</strong><span>Total</span></div>
                </div>
                <div className="dashboard-severity-list">{data.severity.map((item) => <div key={item.name}><span><i style={{ background: SEVERITY_COLORS[item.name] }} />{item.name}</span><strong>{item.value.toLocaleString()}</strong></div>)}</div>
              </div>
            </article>

            <article className="analytics-card dashboard-project-risk">
              <header><div><h2>Project exposure</h2><p>Projects ranked by current results</p></div><span>Top 8</span></header>
              <div className="dashboard-risk-table">
                <div className="dashboard-risk-header"><span>Project</span><span>Scans</span><span>Results</span><span>Exposure</span></div>
                {data.by_project.map((project) => <div className="dashboard-risk-row" key={project.name}><strong>{project.name}</strong><span>{project.scans}</span><span>{project.findings.toLocaleString()}</span><div><i style={{ width: `${Math.max((project.findings / posture.maximumProject) * 100, 2)}%` }} /></div></div>)}
                {!data.by_project.length && <p className="analytics-empty">No project data matches the selected scope.</p>}
              </div>
            </article>

            <article className="analytics-card dashboard-tool-panel">
              <header><div><h2>Scanner contribution</h2><p>Result volume and scan activity</p></div></header>
              <div className="analytics-chart dashboard-tool-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.by_tool} layout="vertical" margin={{ top: 4, right: 12, left: 8, bottom: 0 }}><CartesianGrid stroke={chartGrid} strokeDasharray="3 3" horizontal={false} /><XAxis type="number" stroke={chartText} tickLine={false} axisLine={false} allowDecimals={false} /><YAxis type="category" dataKey="name" width={76} stroke={chartText} tickLine={false} axisLine={false} /><Tooltip contentStyle={tooltipStyle} /><Bar dataKey="findings" name="Results" fill="#4f6bed" radius={[0, 3, 3, 0]} maxBarSize={18} /><Bar dataKey="scans" name="Scans" fill="#22c55e" radius={[0, 3, 3, 0]} maxBarSize={18} /></BarChart></ResponsiveContainer></div>
            </article>

            <article className="analytics-card dashboard-coverage-panel">
              <header><div><h2>Security testing coverage</h2><p>Coverage by scan type</p></div></header>
              <div className="scanner-breakdown">{data.by_scan_type.map((item) => { const maximum = Math.max(...data.by_scan_type.map((entry) => entry.findings), 1); return <div className="scanner-breakdown-row" key={item.name}><div><strong>{item.name}</strong><span>{item.scans} scans · {item.findings} results</span></div><span><i style={{ width: `${Math.max((item.findings / maximum) * 100, 2)}%` }} /></span></div>; })}{!data.by_scan_type.length && <p className="analytics-empty">No scan coverage data matches the selected scope.</p>}</div>
            </article>
          </section>
        </>
      )}
      {data && section === "vulnerabilities" && <DashboardVulnerabilities analytics={data} />}
    </div>
  );
}
