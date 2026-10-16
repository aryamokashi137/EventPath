import { useEffect, useState, useCallback } from "react";
import {
  CalendarDays,
  Clock3,
  Users,
  AlertTriangle,
  FolderKanban,
  CheckCircle,
  Layers,
  Filter,
  Edit,
  Plus,
  Minus,
} from "lucide-react";
import { getProjects, getProjectNetwork } from "../services/projectService";
import { getVendorRecommendations } from "../services/xaiService";
import { updateActivity } from "../services/activityService";
import ExportButtons from "../components/ExportButtons";
import ActivityEditModal from "../components/ActivityEditModal";
import XaiPanel from "../components/XaiPanel";


function Schedule() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState("ALL");
  const [filterCategory, setFilterCategory] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState("gantt"); // 'gantt' | 'vendor'

  // Aggregated data across projects
  const [masterActivities, setMasterActivities] = useState([]);
  const [categories, setCategories] = useState([]);

  // Interactive Gantt Editing Modal State
  const [editingActivity, setEditingActivity] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const loadScheduleData = useCallback(async () => {
    try {
      setLoading(true);
      const projectList = await getProjects();
      setProjects(projectList);

      // Fetch network details for all projects concurrently to compute ES, EF, Float, and timelines
      const networkPromises = projectList.map(async (p) => {
        try {
          const network = await getProjectNetwork(p.id);
          return { project: p, network };
        } catch {
          return { project: p, network: null };
        }
      });

      const results = await Promise.all(networkPromises);
      const aggregated = [];
      const catSet = new Set();

      results.forEach(({ project, network }) => {
        if (!network || !network.nodes) return;

        // Compute baseline date from project start_date or today
        const baseDate = project.start_date ? new Date(project.start_date) : new Date();

        network.nodes.forEach((node) => {
          if (node.id === "START" || node.id === "END") return;

          const category = (node.category || "GENERAL").toUpperCase();
          catSet.add(category);

          const esDays = node.es || 0;
          const durationDays = node.duration || 0;
          const efDays = node.ef || (esDays + durationDays);

          const startDate = new Date(baseDate);
          startDate.setDate(startDate.getDate() + Math.round(esDays));

          const finishDate = new Date(baseDate);
          finishDate.setDate(finishDate.getDate() + Math.round(efDays));

          aggregated.push({
            id: node.id,
            name: node.name,
            projectId: project.id,
            projectName: project.name,
            projectMode: project.mode,
            category,
            duration: durationDays,
            es: esDays,
            ef: efDays,
            slack: node.slack || 0,
            is_critical: Boolean(node.is_critical),
            vendorName: node.vendor_name || "",
            vendorFrom: node.vendor_available_from || "",
            vendorTo: node.vendor_available_to || "",
            startDateStr: startDate.toISOString().split("T")[0],
            finishDateStr: finishDate.toISOString().split("T")[0],
            dependencies: node.dependencies || [],
          });
        });
      });

      setMasterActivities(aggregated);
      setCategories(Array.from(catSet));
    } catch (err) {
      console.error("Error loading portfolio schedule:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadScheduleData();
  }, [loadScheduleData]);

  const handleQuickDurationChange = async (e, act, delta) => {
    e.stopPropagation();
    const newDuration = Math.max(0.5, (act.duration || 1) + delta);
    try {
      await updateActivity(act.projectId, act.id, {
        name: act.name,
        duration: newDuration,
      });
      loadScheduleData();
    } catch (err) {
      console.error("Quick duration change failed:", err);
    }
  };

  // Filter activities
  const filteredActivities = masterActivities.filter((act) => {
    const matchProject = selectedProjectId === "ALL" || act.projectId === selectedProjectId;
    const matchCategory = filterCategory === "ALL" || act.category === filterCategory;
    return matchProject && matchCategory;
  });

  // Calculate max timeline day span
  const maxDay = masterActivities.reduce((max, a) => Math.max(max, a.ef), 10);
  const totalCriticalCount = filteredActivities.filter((a) => a.is_critical).length;
  const totalSlackCount = filteredActivities.filter((a) => a.slack > 0).length;

  if (loading) {
    return (
      <div className="analysis-loading" style={{ minHeight: "60vh", color: "var(--text-secondary)" }}>
        Loading Master Portfolio Schedule...
      </div>
    );
  }

  return (
    <div className="dashboard-page" id="schedule-page-container">
      {/* Hero Header */}
      <section className="dashboard-hero">
        <div>
          <span className="eyebrow">PORTFOLIO MASTER SCHEDULE</span>
          <h1 style={{ color: "var(--text-primary)" }}>Timeline & Milestone Calendar</h1>
          <p style={{ color: "var(--text-secondary)" }}>
            Interactive Gantt timeline, critical path slack visualizer, and vendor booking schedule across all projects.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <ExportButtons
            projectId={selectedProjectId !== "ALL" ? selectedProjectId : null}
            projectName={selectedProjectId !== "ALL" ? projects.find(p => p.id === selectedProjectId)?.name || "Schedule" : "Master_Schedule"}
            targetElementId="schedule-page-container"
          />

          <button
            className={`primary-button ${activeView === "gantt" ? "" : "secondary-action"}`}
            style={{ background: activeView === "gantt" ? "var(--accent)" : "var(--bg-card)", color: activeView === "gantt" ? "#fff" : "var(--text-secondary)", border: "1px solid var(--border-color)" }}
            onClick={() => setActiveView("gantt")}
          >
            <Layers size={17} /> Gantt Timeline
          </button>
          <button
            className={`primary-button ${activeView === "vendor" ? "" : "secondary-action"}`}
            style={{ background: activeView === "vendor" ? "var(--accent)" : "var(--bg-card)", color: activeView === "vendor" ? "#fff" : "var(--text-secondary)", border: "1px solid var(--border-color)" }}
            onClick={() => setActiveView("vendor")}
          >
            <Users size={17} /> Vendor Schedule
          </button>
        </div>
      </section>


      {/* Control Bar: Project Switcher & Filters */}
      <section style={{ display: "flex", flexWrap: "wrap", gap: "16px", alignItems: "center", background: "var(--bg-card)", padding: "16px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <FolderKanban size={18} color="var(--accent)" />
          <strong style={{ fontSize: "0.9rem", color: "var(--text-primary)" }}>Select Project:</strong>
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            style={{ padding: "8px 14px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", fontWeight: 600, color: "var(--text-primary)" }}
          >
            <option value="ALL">🌐 All Projects (Master Portfolio)</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.mode})
              </option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginLeft: "auto" }}>
          <Filter size={16} color="var(--text-secondary)" />
          <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Category:</span>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            style={{ padding: "6px 12px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)" }}
          >
            <option value="ALL">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </section>

      {/* Summary Banner */}
      {/* XAI: vendor conflict recommendations for the selected project */}
      {selectedProjectId !== "ALL" && (
        <section
          className="analysis-panel"
          style={{
            background: "var(--bg-card)",
            padding: "24px",
            borderRadius: "12px",
            border: "1px solid var(--border-color)",
            boxShadow: "var(--shadow-md)",
          }}
        >
          <span className="page-eyebrow">EXPLAINABLE AI</span>
          <h2 style={{ margin: "6px 0 4px", fontSize: "1.15rem" }}>
            Vendor conflict recommendations
          </h2>
          <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: "0.9rem" }}>
            Each double-booking translated into the float shift that clears it
            at no cost to the event date.
          </p>

          <XaiPanel
            fetcher={getVendorRecommendations}
            projectId={selectedProjectId}
          />
        </section>
      )}

      <section className="dashboard-stats" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "var(--accent-light)", color: "var(--accent)" }}>
            <CalendarDays size={20} />
          </div>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Active Timeline Span</span>
            <strong style={{ color: "var(--text-primary)" }}>{Math.ceil(maxDay)} Days Total</strong>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#ef4444" }}>
            <Clock3 size={20} />
          </div>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Critical Path Tasks</span>
            <strong style={{ color: "#ef4444" }}>{totalCriticalCount} Bottlenecks</strong>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: "rgba(34, 197, 94, 0.15)", color: "#16a34a" }}>
            <CheckCircle size={20} />
          </div>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Flexible Slack Tasks</span>
            <strong style={{ color: "#16a34a" }}>{totalSlackCount} Tasks</strong>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: "rgba(245, 158, 11, 0.15)", color: "#d97706" }}>
            <Users size={20} />
          </div>
          <div>
            <span style={{ color: "var(--text-secondary)" }}>Assigned Vendors</span>
            <strong style={{ color: "#d97706" }}>
              {new Set(masterActivities.map((a) => a.vendorName).filter(Boolean)).size} Partners
            </strong>
          </div>
        </div>
      </section>

      {/* VIEW 1: GANTT TIMELINE CHART */}
      {activeView === "gantt" && (
        <section className="analysis-panel" style={{ background: "var(--bg-card)", padding: "24px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
            <div>
              <span className="analysis-eyebrow">CPM / PERT GANTT TIMELINE</span>
              <h2 style={{ margin: "4px 0 0 0", color: "var(--text-primary)" }}>Interactive Event Schedule</h2>
            </div>
            <div style={{ display: "flex", gap: "16px", fontSize: "0.85rem", alignItems: "center", color: "var(--text-secondary)" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: "12px", height: "12px", borderRadius: "3px", background: "#ef4444" }} /> Critical Task (0 Float)
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: "12px", height: "12px", borderRadius: "3px", background: "#6366f1" }} /> Standard Activity
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: "12px", height: "12px", borderRadius: "3px", background: "#cbd5e1" }} /> Slack Window
              </span>
            </div>
          </div>

          {filteredActivities.length === 0 ? (
            <p style={{ color: "var(--text-muted)", padding: "20px 0" }}>No scheduled activities found for selected filter.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              {/* Gantt Header Days Axis */}
              <div style={{ display: "grid", gridTemplateColumns: "280px 130px 120px 1fr", gap: "16px", paddingBottom: "12px", borderBottom: "2px solid var(--border-color)", fontWeight: 700, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                <div>Activity & Project</div>
                <div>Duration (Edit)</div>
                <div>ES → EF</div>
                <div style={{ display: "flex", justifyContent: "space-between", paddingLeft: "10px" }}>
                  <span>Day 0</span>
                  <span>Day {Math.ceil(maxDay / 2)}</span>
                  <span>Day {Math.ceil(maxDay)}</span>
                </div>
              </div>

              {/* Gantt Activity Rows */}
              <div style={{ display: "flex", flexDirection: "column", gap: "12px", paddingTop: "12px" }}>
                {filteredActivities.map((act) => {
                  const startPct = ((act.es || 0) / maxDay) * 100;
                  const durationPct = (Math.max(act.duration || 1, 0.5) / maxDay) * 100;
                  const slackPct = ((act.slack || 0) / maxDay) * 100;
                  const formattedDuration = `${Math.round(Number(act.duration) || 0)}d`;

                  return (
                    <div
                      key={`${act.projectId}-${act.id}`}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "280px 130px 120px 1fr",
                        gap: "16px",
                        alignItems: "center",
                        padding: "10px 0",
                        borderBottom: "1px solid var(--border-color)"
                      }}
                    >
                      {/* Name & Project badge */}
                      <div>
                        <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "6px" }}>
                          {act.is_critical && (
                            <span style={{ background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", border: "1px solid #fecaca", fontSize: "0.65rem", fontWeight: 700, padding: "1px 5px", borderRadius: "4px" }}>
                              CRITICAL
                            </span>
                          )}
                          {act.name}
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "flex", gap: "6px", alignItems: "center" }}>
                          <span>{act.projectName}</span>
                          <span>•</span>
                          <span style={{ textTransform: "uppercase", background: "var(--bg-main)", padding: "1px 5px", borderRadius: "4px", border: "1px solid var(--border-color)" }}>
                            {act.category}
                          </span>
                        </div>
                      </div>

                      {/* Interactive Duration & Edit Button */}
                      <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <button
                          onClick={(e) => handleQuickDurationChange(e, act, -1)}
                          title="Decrease duration by 1 day"
                          style={{
                            padding: "2px 4px",
                            borderRadius: "4px",
                            border: "1px solid var(--border-color)",
                            background: "var(--bg-main)",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <Minus size={12} />
                        </button>
                        <span style={{ fontSize: "0.85rem", fontWeight: 700, minWidth: "26px", textAlign: "center" }}>
                          {formattedDuration}
                        </span>
                        <button
                          onClick={(e) => handleQuickDurationChange(e, act, 1)}
                          title="Increase duration by 1 day"
                          style={{
                            padding: "2px 4px",
                            borderRadius: "4px",
                            border: "1px solid var(--border-color)",
                            background: "var(--bg-main)",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <Plus size={12} />
                        </button>
                        <button
                          onClick={() => {
                            setEditingActivity(act);
                            setIsModalOpen(true);
                          }}
                          title="Edit task details & dependencies"
                          style={{
                            padding: "3px 5px",
                            borderRadius: "4px",
                            border: "none",
                            background: "rgba(99, 102, 241, 0.12)",
                            color: "var(--accent)",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "2px",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            marginLeft: "2px",
                          }}
                        >
                          <Edit size={13} />
                        </button>
                      </div>

                      {/* ES -> EF */}
                      <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                        {Math.round(Number(act.es) || 0)}d → {Math.round(Number(act.ef) || 0)}d
                      </div>

                      {/* Bar Visualization Track */}
                      <div style={{ position: "relative", height: "28px", background: "var(--bg-main)", borderRadius: "6px", overflow: "hidden", display: "flex", alignItems: "center", border: "1px solid var(--border-color)" }}>
                        {/* Task Duration Bar */}
                        <div
                          onClick={() => {
                            setEditingActivity(act);
                            setIsModalOpen(true);
                          }}
                          style={{
                            position: "absolute",
                            left: `${startPct}%`,
                            width: `${Math.max(durationPct, 2)}%`,
                            height: "22px",
                            borderRadius: "4px",
                            background: act.is_critical ? "linear-gradient(90deg, #ef4444, #dc2626)" : "linear-gradient(90deg, #6366f1, #4f46e5)",
                            boxShadow: act.is_critical ? "0 2px 6px rgba(239, 68, 68, 0.3)" : "0 2px 6px rgba(99, 102, 241, 0.2)",
                            display: "flex",
                            alignItems: "center",
                            paddingLeft: "8px",
                            paddingRight: "4px",
                            color: "#ffffff",
                            fontSize: "0.7rem",
                            fontWeight: 700,
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            zIndex: 2,
                            cursor: "pointer",
                          }}
                          title={`Click to edit | Task: ${act.name} | ES: ${Math.round(Number(act.es) || 0)}d, EF: ${Math.round(Number(act.ef) || 0)}d`}
                        >
                          {durationPct > 7 ? formattedDuration : ""}
                        </div>

                        {/* Total Float / Slack Bar */}
                        {act.slack > 0 && (
                          <div
                            style={{
                              position: "absolute",
                              left: `${startPct + durationPct}%`,
                              width: `${slackPct}%`,
                              height: "14px",
                              borderRadius: "0 4px 4px 0",
                              background: "rgba(148, 163, 184, 0.25)",
                              border: "1px dashed var(--text-muted)",
                              zIndex: 1,
                            }}
                            title={`Slack (Float): ${Math.round(Number(act.slack) || 0)} days`}
                          />
                        )}
                      </div>

                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>
      )}

      {/* VIEW 2: VENDOR BOOKING & AVAILABILITY SCHEDULE */}
      {activeView === "vendor" && (
        <section className="analysis-panel" style={{ background: "var(--bg-card)", padding: "24px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
          <div style={{ marginBottom: "20px" }}>
            <span className="analysis-eyebrow">VENDOR LOGISTICS & OVERBOOKING (GAP 5)</span>
            <h2 style={{ margin: "4px 0 0 0", color: "var(--text-primary)" }}>Vendor Booking Calendar</h2>
            <p style={{ margin: "4px 0 0 0", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
              Tracking vendor availability windows, active activity reservations, and overlap constraints.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
            {filteredActivities
              .filter((a) => a.vendorName)
              .map((act) => (
                <div
                  key={`${act.projectId}-${act.id}`}
                  style={{
                    border: "1px solid var(--border-color)",
                    borderRadius: "10px",
                    padding: "16px",
                    background: "var(--bg-main)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "1rem" }}>
                      🤝 {act.vendorName}
                    </span>
                    <span className="mode-badge mode-cpm" style={{ background: "var(--accent-light)", color: "var(--accent)" }}>
                      {act.category}
                    </span>
                  </div>

                  <div style={{ fontSize: "0.875rem", color: "var(--text-primary)" }}>
                    Assigned Task: <strong>{act.name}</strong> ({act.projectName})
                  </div>

                  <div style={{ display: "flex", gap: "16px", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    <span>📅 Reserved: {act.startDateStr} to {act.finishDateStr}</span>
                    <span>⏱️ Duration: {act.duration} days</span>
                  </div>

                  {act.is_critical && (
                    <div style={{ marginTop: "4px", fontSize: "0.75rem", color: "#ef4444", background: "rgba(239, 68, 68, 0.12)", padding: "4px 8px", borderRadius: "6px", border: "1px solid #fecaca" }}>
                      ⚠️ Critical Path Assignment - Delaying this vendor will push the event target completion date.
                    </div>
                  )}
                </div>
              ))}
          </div>
        </section>
      )}

      {/* Interactive Gantt Quick-Edit Modal */}
      <ActivityEditModal
        projectId={editingActivity?.projectId}
        activity={editingActivity}
        allActivities={masterActivities.filter((a) => a.projectId === editingActivity?.projectId)}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingActivity(null);
        }}
        onSaveSuccess={() => {
          loadScheduleData();
        }}
      />
    </div>
  );
}

export default Schedule;
