import { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { RotateCcw, Move, Edit, LayoutGrid } from "lucide-react";

import { getProjectNetwork } from "../services/projectService";
import ExportButtons from "../components/ExportButtons";
import ActivityEditModal from "../components/ActivityEditModal";

function Network() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [network, setNetwork] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Custom dragged node positions saved per project
  const [customPositions, setCustomPositions] = useState(() => {
    try {
      const saved = localStorage.getItem(`eventpath_network_layout_${projectId}`);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  // Modal State for Quick Node Editing
  const [editingNode, setEditingNode] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // =========================================
  // LOAD NETWORK DATA
  // =========================================
  const loadNetwork = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getProjectNetwork(projectId);
      setNetwork(data);
    } catch (err) {
      console.error("Error loading network:", err);
      setError(err.response?.data?.detail || "Failed to load project network.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadNetwork();
  }, [loadNetwork]);

  // =========================================
  // AUTOMATIC TOPOLOGICAL COLUMN LAYOUT ALGORITHM
  // =========================================
  const calculateAutoLayout = useCallback((nodesData = [], edgesData = []) => {
    if (!nodesData.length) return {};

    // Build predecessor adjacency map
    const predecessorsMap = {};
    nodesData.forEach((n) => {
      predecessorsMap[n.id] = [];
    });

    edgesData.forEach((e) => {
      if (predecessorsMap[e.to_node]) {
        predecessorsMap[e.to_node].push(e.from_node);
      }
    });

    // Compute topological column depth for each node
    const depths = { START: 0 };
    let changed = true;
    let passes = 0;
    while (changed && passes < 15) {
      changed = false;
      passes++;
      nodesData.forEach((node) => {
        if (node.id === "START") return;
        const preds = predecessorsMap[node.id] || [];
        let maxPredDepth = 0;
        preds.forEach((pId) => {
          if (depths[pId] !== undefined) {
            maxPredDepth = Math.max(maxPredDepth, depths[pId] + 1);
          }
        });
        const currentDepth = depths[node.id] || 0;
        if (maxPredDepth > currentDepth) {
          depths[node.id] = maxPredDepth;
          changed = true;
        }
      });
    }

    // Force END node to max depth + 1
    const maxDepth = Math.max(...Object.values(depths), 1);
    depths["END"] = maxDepth + 1;

    // Group nodes into column buckets
    const columns = {};
    nodesData.forEach((node) => {
      const d = depths[node.id] !== undefined ? depths[node.id] : 1;
      if (!columns[d]) columns[d] = [];
      columns[d].push(node.id);
    });

    // Calculate X and Y coordinates
    const autoPositions = {};
    Object.keys(columns).forEach((colKey) => {
      const colIndex = parseInt(colKey, 10);
      const nodeIdsInCol = columns[colKey];
      const totalInCol = nodeIdsInCol.length;
      const colX = 50 + colIndex * 280;

      nodeIdsInCol.forEach((nId, rowIndex) => {
        const colY = 220 + rowIndex * 170 - (totalInCol > 1 ? ((totalInCol - 1) * 85) : 0);
        autoPositions[nId] = { x: colX, y: colY };
      });
    });

    return autoPositions;
  }, []);

  const autoPositions = useMemo(() => {
    if (!network?.nodes) return {};
    return calculateAutoLayout(network.nodes, network.edges || []);
  }, [network, calculateAutoLayout]);

  // =========================================
  // CRITICAL PATH CALCULATION
  // =========================================
  const criticalPath = network?.critical_path || [];

  const isCriticalEdge = (sourceId, targetId) => {
    for (let i = 0; i < criticalPath.length - 1; i++) {
      if (criticalPath[i] === sourceId && criticalPath[i + 1] === targetId) {
        return true;
      }
    }
    return false;
  };

  // =========================================
  // NODE DRAG STOP HANDLER (PERSIST POSITIONS)
  // =========================================
  const handleNodeDragStop = (event, node) => {
    const updated = {
      ...customPositions,
      [node.id]: { x: Math.round(node.position.x), y: Math.round(node.position.y) },
    };
    setCustomPositions(updated);
    try {
      localStorage.setItem(`eventpath_network_layout_${projectId}`, JSON.stringify(updated));
    } catch (err) {
      console.error("Failed to persist custom layout:", err);
    }
  };

  const handleResetLayout = () => {
    setCustomPositions({});
    localStorage.removeItem(`eventpath_network_layout_${projectId}`);
  };

  // =========================================
  // BUILD REACT FLOW NODES
  // =========================================
  const flowNodes = useMemo(() => {
    if (!network?.nodes) return [];

    return network.nodes.map((node) => {
      const isCritical = node.is_critical;
      const position = customPositions[node.id] || autoPositions[node.id] || { x: 100, y: 100 };

      return {
        id: node.id,
        position,
        data: {
          label: (
            <div
              className="network-node-content"
              onDoubleClick={() => {
                if (node.id !== "START" && node.id !== "END") {
                  setEditingNode(node);
                  setIsModalOpen(true);
                }
              }}
              style={{ cursor: node.id !== "START" && node.id !== "END" ? "pointer" : "default" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>{node.name}</strong>
                {node.id !== "START" && node.id !== "END" && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingNode(node);
                      setIsModalOpen(true);
                    }}
                    title="Edit Activity"
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--accent, #6366f1)",
                      cursor: "pointer",
                      padding: "2px",
                    }}
                  >
                    <Edit size={13} />
                  </button>
                )}
              </div>

              {node.id !== "START" && node.id !== "END" && (
                <>
                  <span>Duration: {node.duration} days</span>
                  <span>ES: {node.es} &nbsp; EF: {node.ef}</span>
                  <span>LS: {node.ls} &nbsp; LF: {node.lf}</span>
                  <span>Slack: {node.slack}</span>

                  {isCritical && (
                    <span className="network-critical-label">
                      ★ Critical Activity
                    </span>
                  )}
                </>
              )}
            </div>
          ),
        },
        style: {
          width: node.id === "START" || node.id === "END" ? 130 : 210,
          padding: 12,
          borderRadius: 12,
          border:
            node.id === "START" || node.id === "END"
              ? "2px solid #64748b"
              : isCritical
              ? "2px solid #dc2626"
              : "1px solid #cbd5e1",
          background:
            node.id === "START" || node.id === "END"
              ? "var(--bg-main, #f8fafc)"
              : isCritical
              ? "#fef2f2"
              : "var(--bg-card, #ffffff)",
          color: "var(--text-primary)",
          boxShadow: isCritical
            ? "0 6px 18px rgba(220, 38, 38, 0.18)"
            : "0 4px 14px rgba(15, 23, 42, 0.08)",
        },
      };
    });
  }, [network, customPositions, autoPositions]);

  // =========================================
  // BUILD REACT FLOW EDGES (WITH DEPENDENCY LABELS)
  // =========================================
  const flowEdges = useMemo(() => {
    if (!network?.edges) return [];

    return network.edges.map((edge) => {
      const critical = isCriticalEdge(edge.from_node, edge.to_node);
      const depType = edge.dependency_type || "FS";
      const lag = edge.lag || 0;
      const labelText = depType !== "FS" || lag !== 0 ? `${depType}${lag ? ` +${lag}d` : ""}` : "";

      return {
        id: `${edge.from_node}-${edge.to_node}`,
        source: edge.from_node,
        target: edge.to_node,
        type: "smoothstep",
        animated: critical,
        label: labelText,
        labelStyle: { fill: critical ? "#dc2626" : "var(--text-secondary)", fontWeight: 700, fontSize: 11 },
        labelBgStyle: { fill: "var(--bg-card)", rx: 4, ry: 4 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: critical ? "#dc2626" : "#94a3b8",
        },
        style: {
          strokeWidth: critical ? 4 : 2,
          stroke: critical ? "#dc2626" : "#94a3b8",
        },
      };
    });
  }, [network, criticalPath]);

  if (loading) {
    return (
      <div className="network-page">
        <div className="page-loading">Loading project network...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="network-page">
        <div className="error-message">{error}</div>
      </div>
    );
  }

  if (!network) {
    return (
      <div className="network-page">
        <p>No network data available.</p>
      </div>
    );
  }

  const activityNodes = network.nodes?.filter((node) => node.id !== "START" && node.id !== "END") || [];
  const criticalCount = activityNodes.filter((node) => node.is_critical).length;
  const projectDuration = network.nodes?.find((node) => node.id === "END")?.ef || 0;

  return (
    <div className="network-page" id="network-page-container">
      {/* Header */}
      <header className="network-header">
        <div>
          <span className="page-eyebrow">CPM NETWORK</span>
          <h1>Project Network</h1>
          <p>Interactive graph canvas with custom drag layout persistence and explicit dependency edge specs.</p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button
            type="button"
            onClick={handleResetLayout}
            title="Reset node positions to automatic topological column layout"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 14px",
              borderRadius: "8px",
              border: "1px solid var(--border-color)",
              background: "var(--bg-card)",
              color: "var(--text-primary)",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.85rem",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <RotateCcw size={15} /> Reset Layout
          </button>

          <ExportButtons projectId={projectId} projectName="CPM_Network" targetElementId="network-page-container" />

          <button type="button" className="network-back-button" onClick={() => navigate(`/projects/${projectId}`)}>
            ← Back to Project
          </button>
        </div>
      </header>

      {/* Metrics */}
      <section className="network-metrics">
        <div className="network-metric-card">
          <span>Project Duration</span>
          <strong>{Number(projectDuration).toFixed(2)} days</strong>
        </div>
        <div className="network-metric-card">
          <span>Total Activities</span>
          <strong>{activityNodes.length}</strong>
        </div>
        <div className="network-metric-card critical">
          <span>Critical Activities</span>
          <strong>{criticalCount}</strong>
        </div>
        <div className="network-metric-card">
          <span>Critical Path</span>
          <strong>{criticalPath.length} activities</strong>
        </div>
      </section>

      {/* Critical Path List */}
      <section className="critical-path-card">
        <div>
          <span className="page-eyebrow">CRITICAL PATH</span>
          <h2>Activities that determine project completion</h2>
          <p>Activities with zero slack determine the minimum project duration.</p>
        </div>

        <div className="critical-path-list">
          {criticalPath.length > 0 ? (
            criticalPath.map((activityId, index) => {
              const activity = network.nodes?.find((node) => node.id === activityId);
              return (
                <div className="critical-path-item" key={activityId}>
                  <span>{index + 1}</span>
                  <strong>{activity?.name || activityId}</strong>
                  {index < criticalPath.length - 1 && <span className="critical-arrow">→</span>}
                </div>
              );
            })
          ) : (
            <p>No critical path detected.</p>
          )}
        </div>
      </section>

      {/* Legend */}
      <section className="network-legend">
        <div className="legend-item">
          <span className="legend-line critical-line" />
          <span>Critical Path</span>
        </div>
        <div className="legend-item">
          <span className="legend-line normal-line" />
          <span>Normal Dependency</span>
        </div>
        <div className="legend-item">
          <span className="legend-node critical-node" />
          <span>Critical Activity</span>
        </div>
        <div className="legend-item" style={{ marginLeft: "auto", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
          <Move size={14} style={{ display: "inline", verticalAlign: "middle" }} /> Drag nodes to customize layout
        </div>
      </section>

      {/* React Flow Network Diagram Canvas */}
      <section className="network-diagram-card">
        <div className="section-header">
          <div>
            <span className="page-eyebrow">ACTIVITY NETWORK</span>
            <h2>CPM Network Diagram</h2>
            <p>Drag nodes freely to save custom layouts. Double-click any node to open the Quick Activity Editor.</p>
          </div>
        </div>

        <div className="network-canvas">
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            onNodeDragStop={handleNodeDragStop}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            attributionPosition="bottom-left"
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
      </section>

      {/* CPM Table Analysis */}
      <section className="cpm-analysis-card">
        <div className="section-header">
          <div>
            <span className="page-eyebrow">CPM ANALYSIS</span>
            <h2>Activity Schedule Analysis</h2>
            <p>Detailed scheduling calculations for every project activity.</p>
          </div>
        </div>

        <div className="cpm-table-wrapper">
          <table className="cpm-table">
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
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {activityNodes.map((node) => (
                <tr key={node.id} className={node.is_critical ? "critical-row" : ""}>
                  <td>
                    <div className="activity-name-cell">
                      <strong>{node.name}</strong>
                      {node.is_critical && <span className="critical-badge">Critical</span>}
                    </div>
                  </td>
                  <td>{node.duration} days</td>
                  <td>{node.es}</td>
                  <td>{node.ef}</td>
                  <td>{node.ls}</td>
                  <td>{node.lf}</td>
                  <td>
                    <span className={node.slack === 0 ? "slack-zero" : "slack-value"}>{node.slack}</span>
                  </td>
                  <td>
                    {node.is_critical ? (
                      <span className="status-critical">Critical</span>
                    ) : (
                      <span className="status-normal">Non-critical</span>
                    )}
                  </td>
                  <td>
                    <button
                      onClick={() => {
                        setEditingNode(node);
                        setIsModalOpen(true);
                      }}
                      style={{
                        padding: "4px 8px",
                        borderRadius: "6px",
                        border: "1px solid var(--border-color)",
                        background: "var(--bg-main)",
                        cursor: "pointer",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      <Edit size={12} /> Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Node Editing Modal */}
      <ActivityEditModal
        projectId={projectId}
        activity={editingNode}
        allActivities={activityNodes}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingNode(null);
        }}
        onSaveSuccess={() => {
          loadNetwork();
        }}
      />
    </div>
  );
}

export default Network;