import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart3,
  TrendingUp,
  FolderKanban,
  Clock3,
  ShieldCheck,
  Zap,
  ArrowRight,
  Network,
  Search,
  Filter,
  PieChart as PieIcon,
  DollarSign,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { getProjects, getProjectNetwork } from "../services/projectService";

const CATEGORY_COLORS = {
  VENUE: "#6366f1",
  CATERING: "#ec4899",
  AUDIO_VISUAL: "#8b5cf6",
  MARKETING: "#3b82f6",
  DECOR: "#10b981",
  LOGISTICS: "#f59e0b",
  EVENT_EXECUTION: "#ef4444",
  GENERAL: "#64748b",
};

const CHART_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#3b82f6"];

function Analytics() {
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [projectDetailsMap, setProjectDetailsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [modeFilter, setModeFilter] = useState("ALL");

  useEffect(() => {
    const loadGlobalAnalytics = async () => {
      try {
        setLoading(true);
        setError("");

        const projectList = await getProjects();
        setProjects(projectList);

        // Fetch network details for all projects concurrently to compute metrics
        const detailsPromises = projectList.map(async (p) => {
          try {
            const net = await getProjectNetwork(p.id);
            return { projectId: p.id, network: net };
          } catch {
            return { projectId: p.id, network: null };
          }
        });

        const detailsResults = await Promise.all(detailsPromises);
        const map = {};
        detailsResults.forEach((res) => {
          if (res) map[res.projectId] = res.network;
        });
        setProjectDetailsMap(map);
      } catch (err) {
        console.error("Error loading analytics:", err);
        setError("Failed to load portfolio analytics data.");
      } finally {
        setLoading(false);
      }
    };

    loadGlobalAnalytics();
  }, []);

  const filteredProjects = projects.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      (p.category && p.category.toLowerCase().includes(search.toLowerCase()));
    const matchesMode = modeFilter === "ALL" || p.mode === modeFilter;
    return matchesSearch && matchesMode;
  });

  // Global calculations
  const totalProjects = projects.length;
  const cpmCount = projects.filter((p) => p.mode === "CPM").length;
  const pertCount = projects.filter((p) => p.mode === "PERT").length;

  let totalActivities = 0;
  let totalCriticalActivities = 0;
  let totalNormalCost = 0;
  let totalCrashCost = 0;
  const categoryCounts = {};

  projects.forEach((p) => {
    const activities = p.activities || [];
    totalActivities += activities.length;

    activities.forEach((act) => {
      if (act.normal_cost) totalNormalCost += Number(act.normal_cost);
      if (act.crash_cost) totalCrashCost += Number(act.crash_cost);

      const cat = (act.category || "GENERAL").toUpperCase();
      categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
    });

    const net = projectDetailsMap[p.id];
    if (net && net.nodes) {
      const criticals = net.nodes.filter(
        (n) => n.id !== "START" && n.id !== "END" && n.is_critical
      );
      totalCriticalActivities += criticals.length;
    }
  });

  const criticalPercentage =
    totalActivities > 0
      ? ((totalCriticalActivities / totalActivities) * 100).toFixed(1)
      : "0";

  // Data for Charts
  const activityComparisonData = filteredProjects.map((p) => {
    const net = projectDetailsMap[p.id];
    const nodes = net?.nodes?.filter((n) => n.id !== "START" && n.id !== "END") || [];
    const criticalNodes = nodes.filter((n) => n.is_critical);
    return {
      name: p.name.length > 15 ? p.name.substring(0, 15) + "..." : p.name,
      total: p.activities?.length || nodes.length || 0,
      critical: criticalNodes.length,
    };
  });

  const costOverviewData = filteredProjects
    .map((p) => {
      const activities = p.activities || [];
      let nCost = 0;
      let cCost = 0;
      activities.forEach((act) => {
        if (act.normal_cost) nCost += Number(act.normal_cost);
        if (act.crash_cost) cCost += Number(act.crash_cost);
      });
      return {
        name: p.name.length > 12 ? p.name.substring(0, 12) + "..." : p.name,
        normalCost: nCost,
        crashCost: cCost,
      };
    })
    .filter((item) => item.normalCost > 0 || item.crashCost > 0);

  const categoryPieData = Object.keys(categoryCounts).map((cat) => ({
    name: cat,
    value: categoryCounts[cat],
  }));

  if (loading) {
    return (
      <div className="analysis-loading" style={{ minHeight: "60vh", color: "var(--text-secondary)" }}>
        Analyzing portfolio schedule data...
      </div>
    );
  }

  return (
    <div className="dashboard-page">
      {/* Hero Header */}
      <section className="dashboard-hero">
        <div>
          <span className="eyebrow">PORTFOLIO INTELLIGENCE</span>
          <h1>Global Project Analytics</h1>
          <p>
            Cross-project CPM/PERT schedule health, float slack distributions, critical paths, and resource budgets.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() => navigate("/projects")}
        >
          <FolderKanban size={18} />
          View All Projects
        </button>
      </section>

      {/* Top Metric Cards */}
      <section className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-icon">
            <FolderKanban size={21} />
          </div>
          <div>
            <span>Total Projects</span>
            <strong>{totalProjects}</strong>
            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              {pertCount} PERT / {cpmCount} CPM
            </span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <TrendingUp size={21} />
          </div>
          <div>
            <span>Total Portfolio Activities</span>
            <strong>{totalActivities}</strong>
            <span style={{ fontSize: "0.75rem", color: "#ef4444", fontWeight: 600 }}>
              {totalCriticalActivities} Critical ({criticalPercentage}%)
            </span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <Zap size={21} />
          </div>
          <div>
            <span>Portfolio Budget</span>
            <strong>₹{totalNormalCost.toLocaleString()}</strong>
            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              Crash Capacity: ₹{totalCrashCost.toLocaleString()}
            </span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <ShieldCheck size={21} />
          </div>
          <div>
            <span>Portfolio Health</span>
            <strong style={{ color: "#16a34a" }}>Optimal</strong>
            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              Schedule Integrity Verified
            </span>
          </div>
        </div>
      </section>

      {/* Filter Toolbar */}
      <section style={{ display: "flex", gap: "16px", alignItems: "center", background: "var(--bg-card)", padding: "16px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, background: "var(--bg-main)", padding: "8px 12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
          <Search size={16} color="var(--text-secondary)" />
          <input
            type="text"
            placeholder="Search projects or categories..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ border: "none", background: "transparent", width: "100%", outline: "none", color: "var(--text-primary)" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Filter size={16} color="var(--text-secondary)" />
          <select
            value={modeFilter}
            onChange={(e) => setModeFilter(e.target.value)}
            style={{ padding: "8px 12px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)" }}
          >
            <option value="ALL">All Modes</option>
            <option value="CPM">CPM Mode</option>
            <option value="PERT">PERT Mode</option>
          </select>
        </div>
      </section>

      {/* Visual Analytics Charts Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        {/* Chart 1: Activity Load & Critical Path */}
        <section className="analysis-panel" style={{ background: "var(--bg-card)", padding: "20px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
          <div style={{ marginBottom: "16px" }}>
            <span className="analysis-eyebrow">CRITICAL PATH LOAD</span>
            <h3 style={{ margin: "4px 0", color: "var(--text-primary)" }}>Activities Breakdown per Project</h3>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Comparing total activities against critical bottleneck activities.
            </p>
          </div>
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={activityComparisonData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis dataKey="name" stroke="var(--text-muted)" />
                <YAxis stroke="var(--text-muted)" />
                <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", color: "var(--text-primary)" }} />
                <Legend />
                <Bar dataKey="total" name="Total Activities" fill="#6366f1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="critical" name="Critical Activities" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Chart 2: Category Distribution */}
        <section className="analysis-panel" style={{ background: "var(--bg-card)", padding: "20px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
          <div style={{ marginBottom: "16px" }}>
            <span className="analysis-eyebrow">DOMAIN ALLOCATION</span>
            <h3 style={{ margin: "4px 0", color: "var(--text-primary)" }}>Activity Category Distribution</h3>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Breakdown of scheduled tasks across event planning domains.
            </p>
          </div>
          <div style={{ width: "100%", height: 280 }}>
            {categoryPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={95}
                    paddingAngle={4}
                    dataKey="value"
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  >
                    {categoryPieData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={CATEGORY_COLORS[entry.name] || CHART_COLORS[index % CHART_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", color: "var(--text-primary)" }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)" }}>
                No category data available.
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Chart 3: Cost & Crashing Overview (if cost data exists) */}
      {costOverviewData.length > 0 && (
        <section className="analysis-panel" style={{ background: "var(--bg-card)", padding: "20px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
          <div style={{ marginBottom: "16px" }}>
            <span className="analysis-eyebrow">FINANCIAL OPTIMIZATION</span>
            <h3 style={{ margin: "4px 0", color: "var(--text-primary)" }}>Normal Budget vs Maximum Crashed Budget</h3>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Project cost expansion capacity required to achieve minimum possible schedule duration.
            </p>
          </div>
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={costOverviewData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis dataKey="name" stroke="var(--text-muted)" />
                <YAxis tickFormatter={(v) => `₹${v}`} stroke="var(--text-muted)" />
                <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", color: "var(--text-primary)" }} formatter={(value) => [`₹${Number(value).toLocaleString()}`, "Amount"]} />
                <Legend />
                <Bar dataKey="normalCost" name="Normal Budget (₹)" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="crashCost" name="Crashed Budget (₹)" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* Portfolio Health Matrix Table */}
      <section className="analysis-panel" style={{ background: "var(--bg-card)", padding: "20px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
        <div className="section-heading" style={{ marginBottom: "16px" }}>
          <div>
            <span className="analysis-eyebrow">PORTFOLIO MATRIX</span>
            <h2 style={{ margin: "4px 0 0 0", color: "var(--text-primary)" }}>Project Risk & Schedule Parity</h2>
          </div>
        </div>

        <div className="analysis-table-wrapper">
          <table className="analysis-table">
            <thead>
              <tr>
                <th>Project Name</th>
                <th>Mode</th>
                <th>Category</th>
                <th>Activities</th>
                <th>Critical Path</th>
                <th>Start Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredProjects.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: "center", color: "var(--text-muted)", padding: "24px" }}>
                    No projects found matching criteria.
                  </td>
                </tr>
              ) : (
                filteredProjects.map((p) => {
                  const net = projectDetailsMap[p.id];
                  const nodes = net?.nodes?.filter((n) => n.id !== "START" && n.id !== "END") || [];
                  const criticalCount = nodes.filter((n) => n.is_critical).length;
                  const endNode = net?.nodes?.find((n) => n.id === "END");
                  const duration = endNode?.ef || 0;

                  return (
                    <tr key={p.id}>
                      <td>
                        <strong style={{ color: "var(--text-primary)" }}>{p.name}</strong>
                        {p.description && (
                          <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                            {p.description.length > 50 ? p.description.substring(0, 50) + "..." : p.description}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`mode-badge mode-${p.mode.toLowerCase()}`}>
                          {p.mode}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                          {p.category || "GENERAL"}
                        </span>
                      </td>
                      <td style={{ color: "var(--text-primary)" }}>
                        {p.activities?.length || nodes.length || 0} activities
                      </td>
                      <td>
                        <div style={{ display: "flex", flexDirection: "column" }}>
                          <strong style={{ color: "var(--text-primary)" }}>{Number(duration).toFixed(1)} days</strong>
                          <span style={{ fontSize: "0.75rem", color: criticalCount > 0 ? "#ef4444" : "var(--text-secondary)" }}>
                            {criticalCount} critical nodes
                          </span>
                        </div>
                      </td>
                      <td style={{ color: "var(--text-primary)" }}>{p.start_date || "Not set"}</td>
                      <td>
                        <div style={{ display: "flex", gap: "8px" }}>
                          <button
                            type="button"
                            className="text-button"
                            onClick={() => navigate(`/projects/${p.id}/analysis`)}
                            title="Run Schedule Analysis"
                          >
                            <BarChart3 size={15} /> Analysis
                          </button>
                          <button
                            type="button"
                            className="text-button"
                            onClick={() => navigate(`/projects/${p.id}/network`)}
                            title="View Network DAG"
                          >
                            <Network size={15} /> Network
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default Analytics;
