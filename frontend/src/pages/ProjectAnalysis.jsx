import { useEffect, useState } from "react";
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
  getProject,
  getProjectNetwork,
  getProjectPERT,
  simulateProject,
    crashProject,
} from "../services/projectService";

function ProjectAnalysis() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
const [network, setNetwork] = useState(null);
const [pert, setPert] = useState(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState("");

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

        const [projectData, networkData, pertData] =
  await Promise.all([
    getProject(projectId),
    getProjectNetwork(projectId),
    getProjectPERT(projectId),
  ]);

setProject(projectData);
setNetwork(networkData);
setPert(pertData);



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
    <div className="analysis-page">

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

        <div className="analysis-mode-badge">
          <Network size={16} />
          {project.mode}
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
  {Number(projectDuration).toFixed(2)} days
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
          {Number(pertStandardDeviation).toFixed(2)} days
        </strong>
      </div>

    </div>

    {availableTime !== null &&
      availableTime < pertExpectedDuration && (
        <div className="pert-warning">
          The target completion date provides{" "}
          <strong>
            {Number(availableTime).toFixed(2)} days
          </strong>{" "}
          of available time, while the project is
          expected to require{" "}
          <strong>
            {Number(pertExpectedDuration).toFixed(2)} days
          </strong>.
          This results in a very low probability of
          completing the project on time.
        </div>
      )}

  </section>
)}

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
  {Number(activity.duration).toFixed(2)} days
</td>

                    <td>{Number(activity.es).toFixed(2)}</td>

                    <td>
  {Number(activity.ef).toFixed(2)}
</td>

                    <td>{Number(activity.ls).toFixed(2)}</td>

                    <td>
  {Number(activity.lf).toFixed(2)}
</td>

                    <td>{Number(activity.slack).toFixed(2)}</td>

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