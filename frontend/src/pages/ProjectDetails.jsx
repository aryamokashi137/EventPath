
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject } from "../services/projectService";
import {
  createActivity,
  updateActivity,
  deleteActivity,
} from "../services/activityService";
import { useAuth } from "../context/AuthContext";

function ProjectDetails() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [activityName, setActivityName] = useState("");
  const [duration, setDuration] = useState("");
  const [optimisticTime, setOptimisticTime] = useState("");
  const [mostLikelyTime, setMostLikelyTime] = useState("");
  const [pessimisticTime, setPessimisticTime] = useState("");
  const [category, setCategory] = useState("");
  
  // Gap 2: Crashing & Cost fields
  const [crashDuration, setCrashDuration] = useState("");
  const [normalCost, setNormalCost] = useState("");
  const [crashCost, setCrashCost] = useState("");

  // Gap 5: Vendor Availability fields
  const [vendorName, setVendorName] = useState("");
  const [vendorAvailableFrom, setVendorAvailableFrom] = useState("");
  const [vendorAvailableTo, setVendorAvailableTo] = useState("");

  const [predecessorIds, setPredecessorIds] = useState([]);

  const [editingActivityId, setEditingActivityId] = useState(null);

  // =========================
  // LOAD PROJECT
  // =========================
  const loadProject = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getProject(projectId);

      console.log("Loaded project:", data);

      setProject(data);
    } catch (err) {
      console.error("Error loading project:", err);

      setError(
        err.response?.data?.detail ||
          "Failed to load project."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProject();
  }, [projectId]);

  // =========================
  // RESET FORM
  // =========================
  const resetForm = () => {
    setActivityName("");
    setDuration("");
    setOptimisticTime("");
    setMostLikelyTime("");
    setPessimisticTime("");
    setCategory("");
    setCrashDuration("");
    setNormalCost("");
    setCrashCost("");
    setVendorName("");
    setVendorAvailableFrom("");
    setVendorAvailableTo("");
    setPredecessorIds([]);
    setEditingActivityId(null);
  };

  // =========================
  // CREATE ACTIVITY
  // =========================
 const handleCreateActivity = async () => {
  if (!isAdmin) {
    setError("Access Denied: Workspace Administrator privileges ('ADMIN' role) are required to create activities.");
    return;
  }
  if (!activityName.trim()) {
    setError("Please enter an activity name.");
    return;
  }

  if (isPERT) {
    if (
      !optimisticTime ||
      !mostLikelyTime ||
      !pessimisticTime
    ) {
      setError(
        "Please enter optimistic, most likely, and pessimistic times."
      );
      return;
    }

    const optimistic = Number(optimisticTime);
    const mostLikely = Number(mostLikelyTime);
    const pessimistic = Number(pessimisticTime);

    if (
      optimistic <= 0 ||
      mostLikely <= 0 ||
      pessimistic <= 0
    ) {
      setError("PERT estimates must be greater than zero.");
      return;
    }

    if (
      !(optimistic <= mostLikely &&
        mostLikely <= pessimistic)
    ) {
      setError(
        "PERT estimates must follow: Optimistic ≤ Most Likely ≤ Pessimistic."
      );
      return;
    }
  } else {
    if (!duration || Number(duration) <= 0) {
      setError("Please enter a valid duration.");
      return;
    }
  }

  try {
    setSaving(true);
    setError("");

    const payload = {
      name: activityName.trim(),
      duration: isPERT ? 0 : Number(duration),

      optimistic_time: isPERT
        ? Number(optimisticTime)
        : null,

      most_likely_time: isPERT
        ? Number(mostLikelyTime)
        : null,

      pessimistic_time: isPERT
        ? Number(pessimisticTime)
        : null,

      category: category.trim() || null,
      is_milestone: false,
      crash_duration: crashDuration ? Number(crashDuration) : null,
      normal_cost: normalCost ? Number(normalCost) : null,
      crash_cost: crashCost ? Number(crashCost) : null,
      vendor_name: vendorName.trim() || null,
      vendor_available_from: vendorAvailableFrom || null,
      vendor_available_to: vendorAvailableTo || null,
      predecessor_ids: [...predecessorIds],
    };

    console.log("Creating activity with:", payload);

    await createActivity(projectId, payload);

    await loadProject();

    resetForm();
  } catch (err) {
    console.error("Error creating activity:", err);

    setError(
      err.response?.data?.detail ||
        "Failed to create activity."
    );
  } finally {
    setSaving(false);
  }
};

  const handleEditActivity = (activity) => {
    setEditingActivityId(activity.id);
    setActivityName(activity.name);
    setDuration(activity.duration || "");

    setOptimisticTime(activity.optimistic_time || "");
    setMostLikelyTime(activity.most_likely_time || "");
    setPessimisticTime(activity.pessimistic_time || "");
    setCategory(activity.category || "");
    setCrashDuration(activity.crash_duration || "");
    setNormalCost(activity.normal_cost || "");
    setCrashCost(activity.crash_cost || "");
    setVendorName(activity.vendor_name || "");
    setVendorAvailableFrom(activity.vendor_available_from || "");
    setVendorAvailableTo(activity.vendor_available_to || "");

    setPredecessorIds(activity.predecessor_ids || []);

    setError("");
  };

  const handleUpdateActivity = async () => {
    if (!isAdmin) {
      setError("Access Denied: Workspace Administrator privileges ('ADMIN' role) are required to edit activities.");
      return;
    }
    if (!activityName.trim()) {
      setError("Please enter an activity name.");
      return;
    }

    if (!isPERT && (!duration || Number(duration) <= 0)) {
      setError("Please enter a valid duration.");
      return;
    }

    try {
      setSaving(true);
      setError("");

      const payload = {
        name: activityName.trim(),

        duration: isPERT ? 0 : Number(duration),

        optimistic_time: isPERT
          ? Number(optimisticTime)
          : null,

        most_likely_time: isPERT
          ? Number(mostLikelyTime)
          : null,

        pessimistic_time: isPERT
          ? Number(pessimisticTime)
          : null,

        category: category.trim() || null,
        crash_duration: crashDuration ? Number(crashDuration) : null,
        normal_cost: normalCost ? Number(normalCost) : null,
        crash_cost: crashCost ? Number(crashCost) : null,
        vendor_name: vendorName.trim() || null,
        vendor_available_from: vendorAvailableFrom || null,
        vendor_available_to: vendorAvailableTo || null,
        predecessor_ids: [...predecessorIds],
      };

      console.log("Updating activity with:", payload);

      await updateActivity(
        projectId,
        editingActivityId,
        payload
      );


      await loadProject();

      resetForm();
    } catch (err) {
      console.error("Error updating activity:", err);

      setError(
        err.response?.data?.detail ||
          "Failed to update activity."
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteActivity = async (activityId) => {
    if (!isAdmin) {
      alert("Access Denied: Workspace Administrator privileges ('ADMIN' role) are required to delete activities.");
      return;
    }
    const confirmed = window.confirm(
      "Are you sure you want to delete this activity?"
    );

    if (!confirmed) {
      return;
    }

    try {
      setSaving(true);
      setError("");

      await deleteActivity(
        projectId,
        activityId
      );

      await loadProject();

      if (editingActivityId === activityId) {
        resetForm();
      }
    } catch (err) {
      console.error("Error deleting activity:", err);

      setError(
        err.response?.data?.detail ||
          "Failed to delete activity."
      );
    } finally {
      setSaving(false);
    }
  };

  const handlePredecessorChange = (activityId) => {
    setPredecessorIds((currentIds) => {
      let updatedIds;

      if (currentIds.includes(activityId)) {
        // Remove the activity if it was already selected.
        updatedIds = currentIds.filter(
          (id) => id !== activityId
        );
      } else {

        updatedIds = [
          ...currentIds,
          activityId,
        ];
      }

      console.log(
        "Selected predecessor IDs:",
        updatedIds
      );

      return updatedIds;
    });
  };


  if (loading) {
    return <p>Loading project...</p>;
  }


  if (error && !project) {
    return <p>{error}</p>;
  }

  if (!project) {
    return <p>Project not found.</p>;
  }

  const activities = project.activities || [];
  const isPERT = project.mode === "PERT";

  // Activities that can be selected as predecessors.
  const availablePredecessors = activities.filter(
    (activity) =>
      activity.id !== editingActivityId
  );


  return (
    <div className="project-details-page">

      {}
      <button
        type="button"
        onClick={() => navigate("/")}
      >
        ← Back to Projects
      </button>

<button
  type="button"
  className="analyze-project-button"
  onClick={() =>
    navigate(`/projects/${projectId}/analysis`)
  }
>
  Analyze Project →
</button>
      {}
      <header className="project-header">
  <div>
    <h1>{project.name}</h1>

    <p>
      {project.description ||
        "Plan, schedule, and analyze your event."}
    </p>
  </div>

  <div className="project-header-actions">



  </div>
</header>

<header className="project-details-header">

  <div>
    <span className="page-eyebrow">
      PROJECT WORKSPACE
    </span>

    <h1>{project.name}</h1>

    <p>
      {project.description ||
        "Plan and manage your project activities."}
    </p>
  </div>

  <button
    type="button"
    onClick={() =>
      navigate(`/projects/${projectId}/network`)
    }
    className="network-button"
  >
    View CPM Network →
  </button>

</header>
      {}
      <section>
        <h2>Project Information</h2>

        <p>
          <strong>Mode:</strong>{" "}
          {project.mode}
        </p>

        <p>
          <strong>Category:</strong>{" "}
          {project.category}
        </p>

        <p>
          <strong>
            Target Completion:
          </strong>{" "}
          {project.target_completion_date}
        </p>
      </section>

      {/* =========================
          ERROR MESSAGE
          ========================= */}
      {error && (
        <p className="error-message">
          {error}
        </p>
      )}

      {/* =========================
          ACTIVITY FORM
          ========================= */}
      <section>
        <h2>
          {editingActivityId
            ? "Edit Activity"
            : "Add Activity"}
        </h2>

        <div className="activity-form">

          {/* Activity Name */}
          <input
            type="text"
            placeholder="Activity name"
            value={activityName}
            onChange={(e) =>
              setActivityName(e.target.value)
            }
          />

          {/* Duration */}
          {isPERT ? (
  <>
    <input
      type="number"
      placeholder="Optimistic Time (days)"
      value={optimisticTime}
      onChange={(e) =>
        setOptimisticTime(e.target.value)
      }
      min="0.1"
      step="0.1"
    />

    <input
      type="number"
      placeholder="Most Likely Time (days)"
      value={mostLikelyTime}
      onChange={(e) =>
        setMostLikelyTime(e.target.value)
      }
      min="0.1"
      step="0.1"
    />

    <input
      type="number"
      placeholder="Pessimistic Time (days)"
      value={pessimisticTime}
      onChange={(e) =>
        setPessimisticTime(e.target.value)
      }
      min="0.1"
      step="0.1"
    />
  </>
) : (
  <input
    type="number"
    placeholder="Duration (days)"
    value={duration}
    onChange={(e) =>
      setDuration(e.target.value)
    }
    min="0.1"
    step="0.1"
  />
)}

{isPERT && (
  <p className="pert-help-text">
    PERT uses three estimates: optimistic, most likely,
    and pessimistic. Enter values in the order:
    Optimistic ≤ Most Likely ≤ Pessimistic.
  </p>
)}

          {/* Category */}
          <input
            type="text"
            placeholder="Category (e.g. VENUE, CATERING)"
            value={category}
            onChange={(e) =>
              setCategory(e.target.value)
            }
          />

          {/* Gap 2: Crashing Parameters */}
          <div style={{ marginTop: "12px", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px", background: "#f8fafc" }}>
            <p style={{ fontWeight: 600, fontSize: "0.875rem", margin: "0 0 8px 0", color: "#334155" }}>
              ⚡ Schedule Crashing & Costs (Gap 2)
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
              <div>
                <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Crash Duration (days)</label>
                <input
                  type="number"
                  placeholder="Min duration"
                  value={crashDuration}
                  onChange={(e) => setCrashDuration(e.target.value)}
                  min="0.1"
                  step="0.1"
                />
              </div>
              <div>
                <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Normal Cost (₹)</label>
                <input
                  type="number"
                  placeholder="Cost"
                  value={normalCost}
                  onChange={(e) => setNormalCost(e.target.value)}
                  min="0"
                />
              </div>
              <div>
                <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Crash Cost (₹)</label>
                <input
                  type="number"
                  placeholder="Max crash cost"
                  value={crashCost}
                  onChange={(e) => setCrashCost(e.target.value)}
                  min="0"
                />
              </div>
            </div>
          </div>

          {/* Gap 5: Vendor Availability */}
          <div style={{ marginTop: "12px", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "12px", background: "#f8fafc" }}>
            <p style={{ fontWeight: 600, fontSize: "0.875rem", margin: "0 0 8px 0", color: "#334155" }}>
              🤝 Vendor Availability Window (Gap 5)
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gap: "8px" }}>
              <div>
                <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Vendor Name</label>
                <input
                  type="text"
                  placeholder="e.g. Grand Palace Events"
                  value={vendorName}
                  onChange={(e) => setVendorName(e.target.value)}
                />
              </div>
              <div>
                <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Available From</label>
                <input
                  type="date"
                  value={vendorAvailableFrom}
                  onChange={(e) => setVendorAvailableFrom(e.target.value)}
                />
              </div>
              <div>
                <label style={{ fontSize: "0.75rem", color: "#64748b" }}>Available To</label>
                <input
                  type="date"
                  value={vendorAvailableTo}
                  onChange={(e) => setVendorAvailableTo(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* =========================
              PREDECESSOR ACTIVITIES
              ========================= */}
          <div className="predecessor-section">

            <label>
              <strong>
                Predecessor Activities
              </strong>
            </label>

            <p>
              Select one or more activities that
              must be completed before this activity
              starts.
            </p>

            {availablePredecessors.length === 0 ? (
              <p>
                No other activities available.
              </p>
            ) : (
              <div className="predecessor-list">

                {availablePredecessors.map(
                  (activity) => (
                    <label
                      key={activity.id}
                      className="predecessor-option"
                    >
                      <input
                        type="checkbox"
                        checked={predecessorIds.includes(
                          activity.id
                        )}
                        onChange={() =>
                          handlePredecessorChange(
                            activity.id
                          )
                        }
                      />

                      <span>
                        {activity.name}
                      </span>
                    </label>
                  )
                )}

              </div>
            )}

            {/* Selected predecessor summary */}
            <div className="selected-predecessors">
              <strong>
                Selected predecessors:
              </strong>{" "}

              {predecessorIds.length === 0
                ? "None"
                : predecessorIds
                    .map((id) =>
                      activities.find(
                        (activity) =>
                          activity.id === id
                      )
                    )
                    .filter(Boolean)
                    .map(
                      (activity) =>
                        activity.name
                    )
                    .join(", ")}
            </div>

          </div>

          {/* =========================
              SAVE BUTTON
              ========================= */}
          <button
            type="button"
            onClick={
              editingActivityId
                ? handleUpdateActivity
                : handleCreateActivity
            }
            disabled={saving}
          >
            {saving
              ? "Saving..."
              : editingActivityId
              ? "Update Activity"
              : "Add Activity"}
          </button>

          {/* =========================
              CANCEL EDIT
              ========================= */}
          {editingActivityId && (
            <button
              type="button"
              onClick={() => {
                resetForm();
                setError("");
              }}
            >
              Cancel
            </button>
          )}

        </div>
      </section>

      {/* =========================
          ACTIVITIES LIST
          ========================= */}
      <section>
        <h2>
          Activities ({activities.length})
        </h2>

        {activities.length === 0 ? (
          <p>No activities yet.</p>
        ) : (
          activities.map((activity) => {

            const predecessorNames =
              (
                activity.predecessor_ids ||
                []
              )
                .map((id) =>
                  activities.find(
                    (item) =>
                      item.id === id
                  )
                )
                .filter(Boolean)
                .map(
                  (item) => item.name
                );

            return (
              <div
                key={activity.id}
                className="activity-card"
              >

                <h3>
                  {activity.name}
                </h3>

                <p>
                  Duration:{" "}
                  {activity.duration} days
                </p>

                <p>
                  Category:{" "}
                  {activity.category ||
                    "Not specified"}
                </p>

                <p>
                  <strong>
                    Predecessors:
                  </strong>{" "}

                  {predecessorNames.length >
                  0
                    ? predecessorNames.join(
                        ", "
                      )
                    : "None"}
                </p>

                <div className="activity-actions">

                  {/* Edit */}
                  <button
                    type="button"
                    onClick={() =>
                      handleEditActivity(
                        activity
                      )
                    }
                    disabled={saving}
                  >
                    Edit
                  </button>

                  {/* Delete */}
                  <button
                    type="button"
                    onClick={() =>
                      handleDeleteActivity(
                        activity.id
                      )
                    }
                    disabled={saving}
                  >
                    Delete
                  </button>

                </div>

              </div>
            );
          })
        )}
      </section>

    </div>
  );
}

export default ProjectDetails;
