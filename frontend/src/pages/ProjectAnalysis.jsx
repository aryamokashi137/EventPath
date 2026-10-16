import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  BarChart3,
  Clock3,
  Network,
  Target,
  TrendingUp,
} from "lucide-react";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

import ExportButtons from "../components/ExportButtons";
import XaiPanel from "../components/XaiPanel";

import {
  getProject,
  getProjectNetwork,
  getProjectPERT,
  simulateProject,
  crashProject,
  runMonteCarlo,
  checkVendorAvailability,
} from "../services/projectService";

import {
  getCriticalPathExplanation,
  getRiskDiagnostics,
  getCounterfactualCrashing,
  getVendorRecommendations,
} from "../services/xaiService";


function ProjectAnalysis() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [network, setNetwork] = useState(null);
  const [pert, setPert] = useState(null);
  const [availability, setAvailability] = useState(null);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // XAI explanation panels fetch their own reports so a slow Monte Carlo
  // explanation never blocks the deterministic CPM view.
  const [riskParams, setRiskParams] = useState(null);
  const [crashParams, setCrashParams] = useState(null);

  const fetchRiskExplanation = useCallback(
    (id, params) => getRiskDiagnostics(id, params || {}),
    []
  );

  const fetchCrashExplanation = useCallback(
    (id, params) => getCounterfactualCrashing(id, params || {}),
    []
  );

  const [mcNumSimulations, setMcNumSimulations] = useState(1000);
  const [mcTargetTime, setMcTargetTime] = useState("");
  const [mcResult, setMcResult] = useState(null);
  const [mcLoading, setMcLoading] = useState(false);
  const [mcError, setMcError] = useState("");

const [simulationActivity, setSimulationActivity] =
  useState("");

const [simulationDuration, setSimulationDuration] =
  useState("");

const [simulationResult, setSimulationResult] =
  useState(null);

const [simulationLoading, setSimulationLoading] =
  useState(false);

const [simulationError, setSimulationError] =
  useState("");

  const [crashTargetDuration, setCrashTargetDuration] =
  useState("");

const [crashResult, setCrashResult] =
  useState(null);

const [crashLoading, setCrashLoading] =
  useState(false);

const [crashError, setCrashError] =
  useState("");

const [selectedActivityId, setSelectedActivityId] = useState("");


  useEffect(() => {
    const loadAnalysis = async () => {
      try {
        setLoading(true);
        setError("");

        const [projectData, networkData, pertData, availabilityData] =
          await Promise.all([
            getProject(projectId),
            getProjectNetwork(projectId),
            getProjectPERT(projectId),
            checkVendorAvailability(projectId).catch(() => null),
          ]);

        setProject(projectData);
        setNetwork(networkData);
        setPert(pertData);
        setAvailability(availabilityData);



  console.log("PERT data:", pertData);



      } catch (err) {
        console.error("Analysis loading error:", err);

        setError(
          err.response?.data?.detail ||
            "Failed to load project analysis."
        );
      } finally {
        setLoading(false);
      }
    };

    loadAnalysis();
  }, [projectId]);

  const handleSimulation = async () => {
  if (!simulationActivity) {
    setSimulationError("Please select an activity.");
    return;
  }

  if (!simulationDuration || Number(simulationDuration) <= 0) {
    setSimulationError(
      "Please enter a valid duration greater than zero."
    );
    return;
  }

  try {
    setSimulationLoading(true);
    setSimulationError("");
    setSimulationResult(null);

    const result = await simulateProject(
      projectId,
      {
        activity_id: simulationActivity,
        optimistic_time: Number(simulationDuration),
        most_likely_time: Number(simulationDuration),
        pessimistic_time: Number(simulationDuration),
      }
    );

    console.log("Simulation result:", result);

    setSimulationResult(result);
  } catch (err) {
    console.error("Simulation error:", err);

    setSimulationError(
      err.response?.data?.detail ||
        "Failed to run simulation."
    );
  } finally {
    setSimulationLoading(false);
  }
};

const handleCrash = async () => {
  if (
    !crashTargetDuration ||
    Number(crashTargetDuration) <= 0
  ) {
    setCrashError(
      "Please enter a valid target duration greater than zero."
    );
    return;
  }

  if (Number(crashTargetDuration) >= projectDuration) {
    setCrashError(
      `Target duration must be less than the current project duration of ${Number(
        projectDuration
      ).toFixed(2)} days.`
    );
    return;
  }

  try {
    setCrashLoading(true);
    setCrashError("");
    setCrashResult(null);

    const result = await crashProject(
      projectId,
      {
        target_duration: Number(crashTargetDuration),
      }
    );

    console.log("Crash result:", result);

    setCrashResult(result);

    setCrashParams({
      target_duration: Number(crashTargetDuration),
    });
  } catch (err) {
    console.error("Crash error:", err);

    setCrashError(
      err.response?.data?.detail ||
        "Failed to optimize project schedule."
    );
  } finally {
    setCrashLoading(false);
  }
};

  const handleMonteCarlo = async () => {
    try {
      setMcLoading(true);
      setMcError("");
      setMcResult(null);

      const payload = {
        num_simulations: Number(mcNumSimulations) || 1000,
        target_time: mcTargetTime ? Number(mcTargetTime) : null,
      };

    const result = await runMonteCarlo(projectId, payload);
    console.log("Monte Carlo result:", result);
    setMcResult(result);

    setRiskParams({
      num_simulations: payload.num_simulations,
      target_time: payload.target_time,
    });
  } catch (err) {
      console.error("Monte Carlo error:", err);
      setMcError(
        err.response?.data?.detail ||
          "Failed to run Monte Carlo simulation."
      );
    } finally {
      setMcLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="analysis-loading">
        Loading project analysis...
      </div>
    );
  }

  if (error) {
    return (
      <div className="analysis-error">
        <h2>Unable to load analysis</h2>
        <p>{error}</p>

        <button
          onClick={() =>
            navigate(`/projects/${projectId}`)
          }
        >
          Back to Project
        </button>
      </div>
    );
  }

  if (!project || !network) {
    return (
      <div className="analysis-error">
        <h2>Analysis unavailable</h2>
      </div>
    );
  }

  const activityNodes = network.nodes.filter(
    (node) =>
      node.id !== "START" &&
      node.id !== "END"
  );

  const criticalActivities =
    activityNodes.filter(
      (activity) => activity.is_critical
    );

  const projectDuration =
    network.nodes.find(
      (node) => node.id === "END"
    )?.ef || 0;

    const pertExpectedDuration =
  pert?.expected_project_duration ?? projectDuration;

const pertVariance =
  pert?.project_variance ?? 0;

const pertStandardDeviation =
  Math.sqrt(pertVariance);

const pertProbability =
  pert?.probability != null
    ? pert.probability * 100
    : null;

const availableTime =
  pert?.available_time ?? null;

  const criticalPathNames =
    network.critical_path
      .map((id) =>
        activityNodes.find(
          (activity) => activity.id === id
        )
      )
      .filter(Boolean)
      .map((activity) => activity.name);

  return (
    <div className="analysis-page" id="project-analysis-container">

      {/* Header */}

      <header className="analysis-header">

        <div>
          <button
            className="analysis-back-button"
            onClick={() =>
              navigate(`/projects/${projectId}`)
            }
          >
            <ArrowLeft size={17} />
            Back to Project
          </button>

          <div className="analysis-title-row">
            <div>
              <span className="analysis-eyebrow">
                PROJECT ANALYSIS
              </span>

              <h1>{project.name}</h1>

              <p>
                CPM schedule analysis and critical
                path insights.
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <ExportButtons
            projectId={projectId}
            projectName={project.name}
            targetElementId="project-analysis-container"
          />

          <div className="analysis-mode-badge">
            <Network size={16} />
            {project.mode}
          </div>
        </div>

      </header>


      {/* Summary Cards */}

      <section className="analysis-summary-grid">

        <div className="analysis-stat-card">

          <div className="analysis-stat-icon">
            <Clock3 size={21} />
          </div>

          <div>
            <span>Project Duration</span>
            <strong>
  {Math.round(Number(projectDuration) || 0)} days
</strong>
          </div>


        </div>

        <div className="analysis-stat-card">

          <div className="analysis-stat-icon">
            <Target size={21} />
          </div>

          <div>
            <span>Total Activities</span>
            <strong>
              {activityNodes.length}
            </strong>
          </div>

        </div>

        <div className="analysis-stat-card">

          <div className="analysis-stat-icon">
            <TrendingUp size={21} />
          </div>

          <div>
            <span>Critical Activities</span>
            <strong>
              {criticalActivities.length}
            </strong>
          </div>

        </div>

        <div className="analysis-stat-card">

          <div className="analysis-stat-icon">
            <BarChart3 size={21} />
          </div>

          <div>
            <span>Planning Method</span>
            <strong>
              {project.mode}
            </strong>
          </div>

        </div>

      </section>

      {/* XAI: why the critical path is what it is */}

      <section className="analysis-panel">
        <div className="analysis-panel-header">
          <div>
            <span className="analysis-eyebrow">
              EXPLAINABLE AI
            </span>

            <h2>Critical Path Explanation</h2>

            <p>
              Why this path is critical, which float is
              real contingency, and what to do first.
            </p>
          </div>
        </div>

        <XaiPanel
          fetcher={getCriticalPathExplanation}
          projectId={projectId}
        />
      </section>

{/* PERT Analysis */}

{project.mode === "PERT" && pert && (
  <section className="analysis-panel">

    <div className="analysis-panel-header">
      <div>
        <span className="analysis-eyebrow">
          PERT ANALYSIS
        </span>

        <h2>Project Time Estimation</h2>

        <p>
          Statistical analysis of the project's
          expected completion time.
        </p>
      </div>
    </div>

    <div className="pert-results-grid">

     <div className="pert-result-card">
  <span>Completion Probability</span>
  <strong>
    {pertProbability !== null
      ? `${pertProbability < 0.01
          ? pertProbability.toFixed(4)
          : pertProbability.toFixed(2)}%`
      : "Not available"}
  </strong>
</div>

      <div className="pert-result-card">
        <span>Project Variance</span>
        <strong>
          {Number(pertVariance).toFixed(2)}
        </strong>
      </div>

      <div className="pert-result-card">
        <span>Standard Deviation</span>
        <strong>
          ±{Math.round(Number(pertStandardDeviation) || 0)} days
        </strong>
      </div>

    </div>

    {availableTime !== null &&
      availableTime < pertExpectedDuration && (
        <div className="pert-warning">
          The target completion date provides{" "}
          <strong>
            {Math.round(Number(availableTime) || 0)} days
          </strong>{" "}
          of available time, while the project is
          expected to require{" "}
          <strong>
            {Math.round(Number(pertExpectedDuration) || 0)} days
          </strong>.
          This results in a very low probability of
          completing the project on time.
        </div>
      )}

  </section>
)}

{/* XAI: probabilistic risk diagnostics */}

{project.mode === "PERT" && (
  <section className="analysis-panel">
    <div className="analysis-panel-header">
      <div>
        <span className="analysis-eyebrow">
          EXPLAINABLE AI
        </span>

        <h2>Probabilistic Risk Diagnostics</h2>

        <p>
          Completion probability, merge-path bias, hidden
          criticality and a defensible commitment date.
        </p>
      </div>
    </div>

    <XaiPanel
      fetcher={fetchRiskExplanation}
      projectId={projectId}
      params={riskParams}
    />
  </section>
)}

{/* Monte Carlo Risk Assessment */}
<section className="analysis-panel">
  <div className="analysis-panel-header">
    <div>
      <span className="analysis-eyebrow">
        PROBABILISTIC RISK ASSESSMENT
      </span>

      <h2>Monte Carlo PERT Simulation</h2>

      <p>
        Perform stochastic triangular sampling (100–10,000 runs) to resolve
        merge-event path bias, compute completion percentiles (P10–P95),
        activity criticality indices, and cumulative S-Curves.
      </p>
    </div>
  </div>

  <div className="simulation-form">
    <div>
      <label>Number of Simulations</label>
      <select
        value={mcNumSimulations}
        onChange={(e) => setMcNumSimulations(Number(e.target.value))}
      >
        <option value={500}>500 Runs</option>
        <option value={1000}>1,000 Runs (Standard)</option>
        <option value={2500}>2,500 Runs</option>
        <option value={5000}>5,000 Runs (High Precision)</option>
        <option value={10000}>10,000 Runs (Maximum)</option>
      </select>
    </div>

    <div>
      <label>Target Duration (Days, Optional)</label>
      <input
        type="number"
        min="0.1"
        step="0.1"
        value={mcTargetTime}
        onChange={(e) => setMcTargetTime(e.target.value)}
        placeholder={`Default: ${Number(projectDuration).toFixed(2)} days`}
      />
    </div>

    <button
      type="button"
      onClick={handleMonteCarlo}
      disabled={mcLoading}
    >
      {mcLoading ? "Running Simulation..." : "Run Monte Carlo Simulation"}
    </button>
  </div>

  {mcError && (
    <div className="simulation-error">
      {mcError}
    </div>
  )}

  {mcResult && (
    <div className="simulation-result">
      <h3>Monte Carlo Results ({mcResult.num_simulations.toLocaleString()} Runs)</h3>

      <div className="pert-results-grid">
        <div className="pert-result-card">
          <span>Mean Expected Duration</span>
          <strong>{Math.round(Number(mcResult.mean_duration) || 0)} days</strong>
        </div>

        <div className="pert-result-card">
          <span>Standard Deviation</span>
          <strong>±{Math.round(Number(mcResult.std_dev_duration) || 0)} days</strong>
        </div>

        <div className="pert-result-card">
          <span>Duration Range</span>
          <strong>{Math.round(Number(mcResult.min_duration) || 0)} – {Math.round(Number(mcResult.max_duration) || 0)} days</strong>
        </div>

        {mcResult.empirical_probability !== null && (
          <div className="pert-result-card">
            <span>Target Completion Prob.</span>
            <strong>{(mcResult.empirical_probability * 100).toFixed(1)}%</strong>
          </div>
        )}
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        <p style={{ fontWeight: 600, marginBottom: "0.5rem" }}>Schedule Percentiles:</p>
        <div className="pert-results-grid">
          <div className="pert-result-card">
            <span>P10 (Optimistic)</span>
            <strong>{Math.round(Number(mcResult.p10) || 0)} days</strong>
          </div>
          <div className="pert-result-card">
            <span>P50 (Median)</span>
            <strong>{Math.round(Number(mcResult.p50) || 0)} days</strong>
          </div>
          <div className="pert-result-card">
            <span>P80 (Likely)</span>
            <strong>{Math.round(Number(mcResult.p80) || 0)} days</strong>
          </div>
          <div className="pert-result-card">
            <span>P90 (Conservative)</span>
            <strong>{Math.round(Number(mcResult.p90) || 0)} days</strong>
          </div>
          <div className="pert-result-card">
            <span>P95 (Pessimistic)</span>
            <strong>{Math.round(Number(mcResult.p95) || 0)} days</strong>
          </div>
        </div>
      </div>

      {/* S-Curve Chart */}
      {mcResult.s_curve && mcResult.s_curve.length > 0 && (
        <div style={{ marginTop: "2rem" }}>
          <p style={{ fontWeight: 600, marginBottom: "0.25rem" }}>Cumulative Probability S-Curve</p>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
            Probability of project completion by target duration.
          </p>
          <div style={{ width: "100%", height: 300, background: "var(--bg-card)", padding: "16px", borderRadius: "12px", border: "1px solid var(--border-color)" }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mcResult.s_curve}>
                <defs>
                  <linearGradient id="scurveGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis
                  dataKey="duration"
                  tickFormatter={(val) => `${Math.round(Number(val) || 0)}d`}
                  stroke="var(--text-muted)"
                />
                <YAxis
                  domain={[0, 100]}
                  tickFormatter={(val) => `${val}%`}
                  stroke="var(--text-muted)"
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--bg-card)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "8px",
                    color: "var(--text-primary)",
                  }}
                  formatter={(value) => [`${Number(value).toFixed(1)}%`, "Probability"]}
                  labelFormatter={(label) => `Duration: ${Math.round(Number(label) || 0)} days`}
                />
                <Area
                  type="monotone"
                  dataKey="cumulative_probability"
                  stroke="#6366f1"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#scurveGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Criticality Indices Table */}
      {mcResult.criticality_indices && mcResult.criticality_indices.length > 0 && (
        <div style={{ marginTop: "2rem" }}>
          <p style={{ fontWeight: 600, marginBottom: "0.25rem" }}>Activity Criticality Index (Merge-Event Risk)</p>
          <p style={{ fontSize: "0.85rem", color: "#64748b", marginBottom: "1rem" }}>
            Percentage of simulation runs where each activity was on the critical path.
          </p>
          <div className="analysis-table-wrapper">
            <table className="analysis-table">
              <thead>
                <tr>
                  <th>Activity Name</th>
                  <th>Criticality Index (%)</th>
                  <th>Risk Level</th>
                </tr>
              </thead>
              <tbody>
                {mcResult.criticality_indices.map((item) => {
                  const pct = Number(item.criticality_percentage);
                  return (
                    <tr key={item.activity_id}>
                      <td><strong>{item.activity_name}</strong></td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <div style={{ flex: 1, height: "8px", background: "#e2e8f0", borderRadius: "4px", overflow: "hidden" }}>
                            <div
                              style={{
                                width: `${pct}%`,
                                height: "100%",
                                background: pct > 80 ? "#ef4444" : pct > 40 ? "#f59e0b" : "#3b82f6",
                                borderRadius: "4px"
                              }}
                            />
                          </div>
                          <span style={{ fontWeight: 600, minWidth: "45px" }}>{pct.toFixed(1)}%</span>
                        </div>
                      </td>
                      <td>
                        {pct > 80 ? (
                          <span className="critical-badge">High Risk</span>
                        ) : (
                          <span className="normal-badge">Standard</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )}
</section>

{/* Vendor Availability & Overbooking Verification (Gap 5) */}
<section className="analysis-panel">
  <div className="analysis-panel-header">
    <div>
      <span className="analysis-eyebrow">
        RESOURCE & VENDOR CONSTRAINTS
      </span>

      <h2>Vendor Availability & Overbooking Verification</h2>

      <p>
        Audit vendor availability date windows and detect concurrent vendor double-booking conflicts across scheduled activity timelines.
      </p>
    </div>

    <button
      type="button"
      className="analysis-back-button"
      style={{ padding: "8px 16px", borderRadius: "8px", background: "var(--bg-card)", border: "1px solid var(--border-color)", color: "var(--text-primary)", cursor: "pointer" }}
      onClick={async () => {
        setAvailabilityLoading(true);
        const report = await checkVendorAvailability(projectId).catch(() => null);
        setAvailability(report);
        setAvailabilityLoading(false);
      }}
      disabled={availabilityLoading}
    >
      {availabilityLoading ? "Re-checking..." : "Run Vendor Audit"}
    </button>
  </div>

  {availability ? (
    <div style={{ marginTop: "1rem" }}>
      <XaiPanel
        fetcher={getVendorRecommendations}
        projectId={projectId}
      />

      {availability.has_conflicts ? (
        <div style={{ padding: "16px", borderRadius: "12px", background: "rgba(239, 68, 68, 0.12)", border: "1px solid rgba(239, 68, 68, 0.35)", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#ef4444", fontWeight: 700, fontSize: "1.1rem" }}>
            <span>⚠️ {availability.total_conflicts} Vendor Schedule Conflict(s) Detected</span>
          </div>
          <p style={{ margin: "4px 0 0 0", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
            The scheduling engine detected vendor availability date range violations or concurrent vendor double-bookings.
          </p>
        </div>
      ) : (
        <div style={{ padding: "16px", borderRadius: "12px", background: "rgba(34, 197, 94, 0.12)", border: "1px solid rgba(34, 197, 94, 0.35)", marginBottom: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#22c55e", fontWeight: 700, fontSize: "1.1rem" }}>
            <span>✅ All Vendor Constraints Satisfied</span>
          </div>
          <p style={{ margin: "4px 0 0 0", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
            No vendor date range violations or overlapping vendor double-bookings were found across the active schedule.
          </p>
        </div>
      )}

      {availability.conflicts && availability.conflicts.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <h4 style={{ margin: 0 }}>Conflict Report & AI Resolution Advice:</h4>
          {availability.conflicts.map((conflict, index) => (
            <div
              key={index}
              style={{
                border: "1px solid var(--border-color)",
                borderRadius: "12px",
                padding: "16px",
                background: "var(--bg-card)",
                boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span className="critical-badge" style={{ background: conflict.conflict_type === "VENDOR_OVERBOOKING" ? "rgba(124, 58, 237, 0.2)" : "rgba(239, 68, 68, 0.18)", color: conflict.conflict_type === "VENDOR_OVERBOOKING" ? "#a78bfa" : "#ef4444" }}>
                  {conflict.conflict_type === "VENDOR_OVERBOOKING" ? "🤝 VENDOR OVERBOOKING" : "📅 AVAILABILITY WINDOW VIOLATION"}
                </span>
                <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  Available Float: <strong>{Math.round(Number(conflict.total_float) || 0)} days</strong>
                </span>
              </div>

              <h4 style={{ margin: "4px 0 8px 0", fontSize: "1rem" }}>
                Activity: <strong>{conflict.activity_name}</strong> {conflict.vendor_name && `(Vendor: ${conflict.vendor_name})`}
              </h4>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: "12px" }}>
                <div>
                  <strong>Scheduled Dates:</strong> {conflict.scheduled_start} to {conflict.scheduled_finish}
                </div>
                {conflict.conflict_type === "VENDOR_AVAILABILITY_VIOLATION" ? (
                  <div>
                    <strong>Vendor Window:</strong> {conflict.available_from || "N/A"} to {conflict.available_to || "N/A"}
                  </div>
                ) : (
                  <div>
                    <strong>Conflicting Activity:</strong> {conflict.conflicting_activity_name || "N/A"}
                  </div>
                )}
              </div>

              <div style={{ padding: "10px 12px", borderRadius: "8px", background: "var(--bg-main)", borderLeft: "4px solid #6366f1", fontSize: "0.875rem", color: "var(--text-primary)" }}>
                <strong>💡 Recommended Resolution:</strong> {conflict.resolution_recommendation}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  ) : (
    <p style={{ color: "#64748b" }}>Vendor audit data not available.</p>
  )}
</section>

{/* What-If Simulation */}

<section className="analysis-panel">

  <div className="analysis-panel-header">
    <div>
      <span className="analysis-eyebrow">
        WHAT-IF ANALYSIS
      </span>

      <h2>Project Simulation</h2>

      <p>
        Test a hypothetical activity duration
        without changing the actual project.
      </p>
    </div>
  </div>

  <div className="simulation-form">

    <div>
      <label>
        Activity
      </label>

      <select
        value={simulationActivity}
        onChange={(e) =>
          setSimulationActivity(e.target.value)
        }
      >
        <option value="">
          Select an activity
        </option>

        {activityNodes.map((activity) => (
          <option
            key={activity.id}
            value={activity.id}
          >
            {activity.name}
          </option>
        ))}
      </select>
    </div>

    <div>
      <label>
        Hypothetical Duration (days)
      </label>

      <input
        type="number"
        min="0.01"
        step="0.01"
        value={simulationDuration}
        onChange={(e) =>
          setSimulationDuration(e.target.value)
        }
        placeholder="Enter duration"
      />
    </div>

    <button
      type="button"
      onClick={handleSimulation}
      disabled={simulationLoading}
    >
      {simulationLoading
        ? "Running Simulation..."
        : "Run Simulation"}
    </button>

  </div>

  {simulationError && (
    <div className="simulation-error">
      {simulationError}
    </div>
  )}

  {simulationResult && (
    <div className="simulation-result">

      <h3>Simulation Result</h3>

      <p>
        New Project Duration:{" "}
        <strong>
          {Number(
            simulationResult.new_project_duration
          ).toFixed(2)}{" "}
          days
        </strong>
      </p>

      <p>
        New Completion Probability:{" "}
        <strong>
          {simulationResult.new_completion_probability !== null
            ? `${(
                simulationResult.new_completion_probability * 100
              ).toFixed(4)}%`
            : "Not available"}
        </strong>
      </p>

      <p>
        Critical Activities:
      </p>

      <ul>
        {simulationResult.new_critical_path.map(
          (id) => {
            const activity = activityNodes.find(
              (item) => item.id === id
            );

            return (
              <li key={id}>
                {activity
                  ? activity.name
                  : id}
              </li>
            );
          }
        )}
      </ul>

      {simulationResult.flipped_to_critical.length > 0 && (
        <>
          <p>
            <strong>
              Activities that became critical:
            </strong>
          </p>

          <ul>
            {simulationResult.flipped_to_critical.map(
              (id) => {
                const activity =
                  activityNodes.find(
                    (item) => item.id === id
                  );

                return (
                  <li key={id}>
                    {activity
                      ? activity.name
                      : id}
                  </li>
                );
              }
            )}
          </ul>
        </>
      )}

      {simulationResult.flipped_to_non_critical.length > 0 && (
        <>
          <p>
            <strong>
              Activities that are no longer critical:
            </strong>
          </p>

          <ul>
            {simulationResult.flipped_to_non_critical.map(
              (id) => {
                const activity =
                  activityNodes.find(
                    (item) => item.id === id
                  );

                return (
                  <li key={id}>
                    {activity
                      ? activity.name
                      : id}
                  </li>
                );
              }
            )}
          </ul>
        </>
      )}

    </div>
  )}

</section>

      {/* Schedule Crashing */}

      <section className="analysis-panel">

        <div className="analysis-panel-header">
          <div>
            <span className="analysis-eyebrow">
              SCHEDULE OPTIMIZATION
            </span>

            <h2>Schedule Crashing</h2>

            <p>
              Reduce the project duration by compressing
              critical activities at an additional cost.
            </p>
          </div>
        </div>

        <XaiPanel
          fetcher={fetchCrashExplanation}
          projectId={projectId}
          params={crashParams}
        />

        <div className="crash-form">

          <div>
            <label>
              Target Duration (days)
            </label>

            <input
              type="number"
              min="0.01"
              step="0.01"
              value={crashTargetDuration}
              onChange={(e) =>
                setCrashTargetDuration(e.target.value)
              }
              placeholder={`Current: ${Number(
                projectDuration
              ).toFixed(2)} days`}
            />
          </div>

          <button
            type="button"
            onClick={handleCrash}
            disabled={crashLoading}
          >
            {crashLoading
              ? "Optimizing Schedule..."
              : "Optimize Schedule"}
          </button>

        </div>

        {crashError && (
          <div className="crash-error">
            {crashError}
          </div>
        )}

        {crashResult && (
          <div className="crash-result">

            <h3>Optimization Result</h3>

            <div className="crash-results-grid">

              <div className="crash-result-card">
                <span>Original Duration</span>
                <strong>
                  {Number(
                    crashResult.original_duration
                  ).toFixed(2)}{" "}
                  days
                </strong>
              </div>

              <div className="crash-result-card">
                <span>Crashed Duration</span>
                <strong>
                  {Number(
                    crashResult.crashed_duration
                  ).toFixed(2)}{" "}
                  days
                </strong>
              </div>

              <div className="crash-result-card">
                <span>Days Saved</span>
                <strong>
                  {Number(
                    crashResult.total_days_saved
                  ).toFixed(2)}{" "}
                  days
                </strong>
              </div>

              <div className="crash-result-card">
                <span>Additional Crash Cost</span>
                <strong>
                  ₹
                  {Number(
                    crashResult.additional_crash_cost
                  ).toFixed(2)}
                </strong>
              </div>

              <div className="crash-result-card">
                <span>Final Total Cost</span>
                <strong>
                  ₹
                  {Number(
                    crashResult.final_total_cost
                  ).toFixed(2)}
                </strong>
              </div>

            </div>

            {crashResult.crashed_activities &&
              crashResult.crashed_activities.length > 0 && (
                <>
                  <p>
                    <strong>
                      Crashed Activities:
                    </strong>
                  </p>

                  <ul>
                    {crashResult.crashed_activities.map(
                      (activity) => (
                        <li key={activity.activity_id}>
                          <strong>
                            {activity.activity_name}
                          </strong>
                          {" — "}
                          {Number(
                            activity.original_duration
                          ).toFixed(2)}
                          {" → "}
                          {Number(
                            activity.crashed_duration
                          ).toFixed(2)}
                          {" days"}
                          {" ("}
                          {Number(
                            activity.days_crashed
                          ).toFixed(2)}
                          {" days saved, ₹"}
                          {Number(
                            activity.total_crash_cost
                          ).toFixed(2)}
                          {" cost)"}
                        </li>
                      )
                    )}
                  </ul>
                </>
              )}

            {crashResult.final_critical_path &&
              crashResult.final_critical_path.length > 0 && (
                <>
                  <p>
                    <strong>
                      Final Critical Activities:
                    </strong>
                  </p>

                  <ul>
                    {crashResult.final_critical_path.map(
                      (id) => {
                        const activity =
                          activityNodes.find(
                            (item) => item.id === id
                          );

                        return (
                          <li key={id}>
                            {activity
                              ? activity.name
                              : id}
                          </li>
                        );
                      }
                    )}
                  </ul>
                </>
              )}

          </div>
        )}

      </section>

      {/* CPM Table */}

      <section className="analysis-panel">

        <div className="analysis-panel-header">

          <div>
            <span className="analysis-eyebrow">
              SCHEDULE DETAILS
            </span>

            <h2>CPM Activity Analysis</h2>

            <p>
              Early and late schedule calculations
              for every activity.
            </p>
          </div>

        </div>

        <div className="analysis-table-wrapper">

          <table className="analysis-table">

            <thead>
              <tr>
                <th>Activity</th>
                <th>Duration</th>
                <th>ES</th>
                <th>EF</th>
                <th>LS</th>
                <th>LF</th>
                <th>Slack</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>

              {activityNodes.map(
                (activity) => (
                  <tr key={activity.id}>

                    <td>
                      <strong>
                        {activity.name}
                      </strong>
                    </td>

                    <td>
  {Math.round(Number(activity.duration) || 0)} days
</td>

                    <td>{Math.round(Number(activity.es) || 0)}</td>

                    <td>
  {Math.round(Number(activity.ef) || 0)}
</td>

                    <td>{Math.round(Number(activity.ls) || 0)}</td>

                    <td>
  {Math.round(Number(activity.lf) || 0)}
</td>

                    <td>{Math.round(Number(activity.slack) || 0)}</td>


                    <td>

                      {activity.is_critical ? (
                        <span className="critical-badge">
                          Critical
                        </span>
                      ) : (
                        <span className="normal-badge">
                          Flexible
                        </span>
                      )}

                    </td>

                  </tr>
                )
              )}

            </tbody>

          </table>

        </div>

      </section>

    </div>
  );
}

export default ProjectAnalysis;