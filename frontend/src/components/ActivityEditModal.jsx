import { useState } from "react";
import { X, Save, Clock, Users, Link as LinkIcon, AlertTriangle } from "lucide-react";
import { updateActivity } from "../services/activityService";

export default function ActivityEditModal({
  projectId,
  activity,
  allActivities = [],
  isOpen,
  onClose,
  onSaveSuccess,
}) {
  if (!isOpen || !activity) return null;

  const [name, setName] = useState(activity.name || "");
  const [duration, setDuration] = useState(activity.duration || 1);
  const [category, setCategory] = useState(activity.category || "GENERAL");
  const [optimistic, setOptimistic] = useState(activity.optimistic_time || activity.duration || 1);
  const [mostLikely, setMostLikely] = useState(activity.most_likely_time || activity.duration || 1);
  const [pessimistic, setPessimistic] = useState(activity.pessimistic_time || activity.duration || 1);
  const [vendorName, setVendorName] = useState(activity.vendor_name || activity.vendorName || "");
  const [vendorFrom, setVendorFrom] = useState(activity.vendor_available_from || activity.vendorFrom || "");
  const [vendorTo, setVendorTo] = useState(activity.vendor_available_to || activity.vendorTo || "");

  // Structured dependencies state: array of { predecessor_id, dependency_type, lag }
  const [dependencies, setDependencies] = useState(() => {
    if (activity.dependencies && Array.isArray(activity.dependencies) && activity.dependencies.length > 0) {
      return activity.dependencies.map((d) => ({
        predecessor_id: d.predecessor_id || d.pred_id || d.id,
        dependency_type: d.dependency_type || "FS",
        lag: d.lag || 0,
      }));
    }
    if (activity.predecessor_ids && Array.isArray(activity.predecessor_ids)) {
      return activity.predecessor_ids.map((id) => ({
        predecessor_id: id,
        dependency_type: "FS",
        lag: 0,
      }));
    }
    return [];
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const possiblePredecessors = allActivities.filter((a) => a.id !== activity.id && a.id !== "START" && a.id !== "END");

  const handleAddDependency = (predId) => {
    if (!predId) return;
    if (dependencies.some((d) => d.predecessor_id === predId)) return;
    setDependencies([...dependencies, { predecessor_id: predId, dependency_type: "FS", lag: 0 }]);
  };

  const handleRemoveDependency = (predId) => {
    setDependencies(dependencies.filter((d) => d.predecessor_id !== predId));
  };

  const handleUpdateDependency = (predId, field, value) => {
    setDependencies(
      dependencies.map((d) => {
        if (d.predecessor_id === predId) {
          return { ...d, [field]: field === "lag" ? parseFloat(value) || 0 : value };
        }
        return d;
      })
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      setError("");

      const payload = {
        name,
        duration: parseFloat(duration) || 1,
        category: category.toUpperCase(),
        optimistic_time: parseFloat(optimistic) || parseFloat(duration) || 1,
        most_likely_time: parseFloat(mostLikely) || parseFloat(duration) || 1,
        pessimistic_time: parseFloat(pessimistic) || parseFloat(duration) || 1,
        vendor_name: vendorName || null,
        vendor_available_from: vendorFrom || null,
        vendor_available_to: vendorTo || null,
        dependencies: dependencies.map((d) => ({
          predecessor_id: d.predecessor_id,
          dependency_type: d.dependency_type,
          lag: parseFloat(d.lag) || 0,
        })),
      };

      const updated = await updateActivity(projectId, activity.id, payload);
      if (onSaveSuccess) {
        onSaveSuccess(updated);
      }
      onClose();
    } catch (err) {
      console.error("Failed to update activity:", err);
      setError(err.response?.data?.detail || "Failed to update activity details.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "20px",
      }}
    >
      <div
        style={{
          background: "var(--bg-card, #ffffff)",
          borderRadius: "16px",
          width: "100%",
          maxWidth: "620px",
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)",
          border: "1px solid var(--border-color, #e2e8f0)",
          color: "var(--text-primary, #0f172a)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid var(--border-color, #e2e8f0)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: 700,
                color: "var(--accent, #6366f1)",
                letterSpacing: "0.05em",
                textTransform: "uppercase",
              }}
            >
              GANTT / NETWORK ACTIVITY EDITOR
            </span>
            <h2 style={{ margin: "2px 0 0 0", fontSize: "1.25rem", color: "var(--text-primary, #0f172a)" }}>
              Edit Task: {activity.name}
            </h2>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-secondary, #64748b)",
              padding: "4px",
              borderRadius: "6px",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div
            style={{
              margin: "16px 24px 0",
              padding: "12px 16px",
              borderRadius: "8px",
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid #fecaca",
              color: "#ef4444",
              fontSize: "0.875rem",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* General Specs */}
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "6px" }}>
                Activity Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: "1px solid var(--border-color, #cbd5e1)",
                  background: "var(--bg-main, #f8fafc)",
                  color: "var(--text-primary)",
                  fontWeight: 500,
                }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "6px" }}>
                Duration (Days)
              </label>
              <input
                type="number"
                step="0.5"
                min="0.1"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                required
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: "1px solid var(--border-color, #cbd5e1)",
                  background: "var(--bg-main, #f8fafc)",
                  color: "var(--text-primary)",
                  fontWeight: 600,
                }}
              />
            </div>
          </div>

          {/* PERT Estimates */}
          <div
            style={{
              padding: "16px",
              borderRadius: "10px",
              background: "var(--bg-main, #f8fafc)",
              border: "1px solid var(--border-color, #e2e8f0)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
              <Clock size={16} color="var(--accent, #6366f1)" />
              <strong style={{ fontSize: "0.875rem" }}>PERT 3-Point Estimate (Optional)</strong>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-secondary)" }}>Optimistic (a)</label>
                <input
                  type="number"
                  step="0.5"
                  value={optimistic}
                  onChange={(e) => setOptimistic(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: "6px",
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-card)",
                    color: "var(--text-primary)",
                  }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-secondary)" }}>Most Likely (m)</label>
                <input
                  type="number"
                  step="0.5"
                  value={mostLikely}
                  onChange={(e) => setMostLikely(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: "6px",
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-card)",
                    color: "var(--text-primary)",
                  }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-secondary)" }}>Pessimistic (b)</label>
                <input
                  type="number"
                  step="0.5"
                  value={pessimistic}
                  onChange={(e) => setPessimistic(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: "6px",
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-card)",
                    color: "var(--text-primary)",
                  }}
                />
              </div>
            </div>
          </div>

          {/* Activity Dependencies (FS, SS, FF, SF + Lag) */}
          <div
            style={{
              padding: "16px",
              borderRadius: "10px",
              background: "var(--bg-main, #f8fafc)",
              border: "1px solid var(--border-color, #e2e8f0)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <LinkIcon size={16} color="var(--accent, #6366f1)" />
                <strong style={{ fontSize: "0.875rem" }}>Predecessors & Dependency Types</strong>
              </div>
              {possiblePredecessors.length > 0 && (
                <select
                  onChange={(e) => {
                    handleAddDependency(e.target.value);
                    e.target.value = "";
                  }}
                  style={{
                    padding: "4px 8px",
                    borderRadius: "6px",
                    fontSize: "0.8rem",
                    border: "1px solid var(--border-color)",
                  }}
                >
                  <option value="">+ Add Predecessor</option>
                  {possiblePredecessors.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {dependencies.length === 0 ? (
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: 0 }}>
                No predecessor dependencies defined (starts at project start).
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {dependencies.map((dep) => {
                  const predObj = allActivities.find((a) => a.id === dep.predecessor_id);
                  return (
                    <div
                      key={dep.predecessor_id}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "2fr 1.2fr 1fr 32px",
                        gap: "8px",
                        alignItems: "center",
                        padding: "8px",
                        background: "var(--bg-card)",
                        borderRadius: "8px",
                        border: "1px solid var(--border-color)",
                      }}
                    >
                      <span style={{ fontSize: "0.85rem", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis" }}>
                        {predObj?.name || dep.predecessor_id}
                      </span>
                      <select
                        value={dep.dependency_type}
                        onChange={(e) => handleUpdateDependency(dep.predecessor_id, "dependency_type", e.target.value)}
                        style={{ padding: "4px 6px", borderRadius: "4px", fontSize: "0.8rem" }}
                      >
                        <option value="FS">Finish-to-Start (FS)</option>
                        <option value="SS">Start-to-Start (SS)</option>
                        <option value="FF">Finish-to-Finish (FF)</option>
                        <option value="SF">Start-to-Finish (SF)</option>
                      </select>
                      <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>Lag:</span>
                        <input
                          type="number"
                          step="0.5"
                          value={dep.lag}
                          onChange={(e) => handleUpdateDependency(dep.predecessor_id, "lag", e.target.value)}
                          style={{ width: "45px", padding: "2px 4px", fontSize: "0.8rem", borderRadius: "4px", border: "1px solid var(--border-color)" }}
                        />
                        <span style={{ fontSize: "0.75rem" }}>d</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveDependency(dep.predecessor_id)}
                        style={{ background: "none", border: "none", color: "#ef4444", cursor: "pointer" }}
                      >
                        <X size={16} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Vendor Logistics */}
          <div
            style={{
              padding: "16px",
              borderRadius: "10px",
              background: "var(--bg-main, #f8fafc)",
              border: "1px solid var(--border-color, #e2e8f0)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
              <Users size={16} color="var(--accent, #6366f1)" />
              <strong style={{ fontSize: "0.875rem" }}>Vendor Assignment (Gap 5 Logistics)</strong>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-secondary)" }}>Vendor Partner Name</label>
                <input
                  type="text"
                  placeholder="e.g. StagePro Inc, SoundCraft LLC"
                  value={vendorName}
                  onChange={(e) => setVendorName(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    borderRadius: "6px",
                    border: "1px solid var(--border-color)",
                    background: "var(--bg-card)",
                    color: "var(--text-primary)",
                  }}
                />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-secondary)" }}>Available From</label>
                  <input
                    type="date"
                    value={vendorFrom}
                    onChange={(e) => setVendorFrom(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "6px 8px",
                      borderRadius: "6px",
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-card)",
                      color: "var(--text-primary)",
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-secondary)" }}>Available To</label>
                  <input
                    type="date"
                    value={vendorTo}
                    onChange={(e) => setVendorTo(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "6px 8px",
                      borderRadius: "6px",
                      border: "1px solid var(--border-color)",
                      background: "var(--bg-card)",
                      color: "var(--text-primary)",
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", justifySelf: "flex-end", gap: "12px", marginTop: "12px" }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "10px 18px",
                borderRadius: "8px",
                border: "1px solid var(--border-color)",
                background: "var(--bg-card)",
                color: "var(--text-secondary)",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              style={{
                padding: "10px 22px",
                borderRadius: "8px",
                border: "none",
                background: "var(--accent, #6366f1)",
                color: "#ffffff",
                fontWeight: 700,
                cursor: saving ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                boxShadow: "0 4px 12px rgba(99, 102, 241, 0.3)",
              }}
            >
              <Save size={16} />
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
