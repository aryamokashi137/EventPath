import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";

import { getProjectNetwork } from "../services/projectService";

function Network() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [network, setNetwork] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // =========================================
  // LOAD NETWORK
  // =========================================

  useEffect(() => {
    const loadNetwork = async () => {
      try {
        setLoading(true);
        setError("");

        const data = await getProjectNetwork(projectId);

        console.log("Network data:", data);

        setNetwork(data);
      } catch (err) {
        console.error("Error loading network:", err);

        setError(
          err.response?.data?.detail ||
            "Failed to load project network."
        );
      } finally {
        setLoading(false);
      }
    };

    loadNetwork();
  }, [projectId]);

  // =========================================
  // CRITICAL PATH SET
  // =========================================

  const criticalPath = network?.critical_path || [];

  // =========================================
  // CHECK WHETHER AN EDGE IS ON CRITICAL PATH
  // =========================================

  const isCriticalEdge = (sourceId, targetId) => {
    for (let i = 0; i < criticalPath.length - 1; i++) {
      if (
        criticalPath[i] === sourceId &&
        criticalPath[i + 1] === targetId
      ) {
        return true;
      }
    }

    return false;
  };

  // =========================================
  // CREATE REACT FLOW NODES
  // =========================================

  const nodes = useMemo(() => {
    if (!network?.nodes) {
      return [];
    }

    return network.nodes.map((node) => {
      const isCritical = node.is_critical;

      // Temporary layout for the current project.
      // We will make this automatic later.
      let position = {
        x: 300,
        y: 500,
      };

      if (node.id === "START") {
        position = {
          x: 0,
          y: 250,
        };
      } else if (node.id === "END") {
        position = {
          x: 900,
          y: 250,
        };
      } else if (node.name === "Arrange Catering") {
        position = {
          x: 300,
          y: 100,
        };
      } else if (node.name === "book venue") {
        position = {
          x: 300,
          y: 400,
        };
      } else if (node.name === "test both") {
        position = {
          x: 600,
          y: 250,
        };
      } else if (node.name === "send invitations") {
        position = {
          x: 600,
          y: 500,
        };
      }

      return {
        id: node.id,

        position,

        data: {
          label: (
            <div className="network-node-content">
              <strong>{node.name}</strong>

              {node.id !== "START" &&
                node.id !== "END" && (
                  <>
                    <span>
                      Duration: {node.duration} days
                    </span>

                    <span>
                      ES: {node.es} &nbsp; EF: {node.ef}
                    </span>

                    <span>
                      LS: {node.ls} &nbsp; LF: {node.lf}
                    </span>

                    <span>
                      Slack: {node.slack}
                    </span>

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
          width:
            node.id === "START" ||
            node.id === "END"
              ? 130
              : 210,

          padding: 12,

          borderRadius: 12,

          border:
            node.id === "START" ||
            node.id === "END"
              ? "2px solid #64748b"
              : isCritical
              ? "2px solid #dc2626"
              : "1px solid #d1d5db",

          background:
            node.id === "START" ||
            node.id === "END"
              ? "#f8fafc"
              : isCritical
              ? "#fef2f2"
              : "#ffffff",

          color: "#111827",

          boxShadow: isCritical
            ? "0 6px 18px rgba(220, 38, 38, 0.18)"
            : "0 4px 14px rgba(15, 23, 42, 0.06)",
        },
      };
    });
  }, [network]);

  // =========================================
  // CREATE REACT FLOW EDGES
  // =========================================

  const edges = useMemo(() => {
    if (!network?.edges) {
      return [];
    }

    return network.edges.map((edge) => {
      const critical = isCriticalEdge(
        edge.from_node,
        edge.to_node
      );

      return {
        id: `${edge.from_node}-${edge.to_node}`,

        source: edge.from_node,
        target: edge.to_node,

        type: "smoothstep",

        animated: critical,

        markerEnd: {
          type: MarkerType.ArrowClosed,

          color: critical
            ? "#dc2626"
            : "#94a3b8",
        },

        style: {
          strokeWidth: critical ? 4 : 2,

          stroke: critical
            ? "#dc2626"
            : "#94a3b8",
        },
      };
    });
  }, [network, criticalPath]);

  // =========================================
  // LOADING
  // =========================================

  if (loading) {
    return (
      <div className="network-page">
        <div className="page-loading">
          Loading project network...
        </div>
      </div>
    );
  }

  // =========================================
  // ERROR
  // =========================================

  if (error) {
    return (
      <div className="network-page">
        <div className="error-message">
          {error}
        </div>
      </div>
    );
  }

  // =========================================
  // NO DATA
  // =========================================

  if (!network) {
    return (
      <div className="network-page">
        <p>No network data available.</p>
      </div>
    );
  }

  // =========================================
  // METRICS
  // =========================================

  const activityNodes =
    network.nodes?.filter(
      (node) =>
        node.id !== "START" &&
        node.id !== "END"
    ) || [];

  const criticalCount =
    activityNodes.filter(
      (node) => node.is_critical
    ).length;

  const projectDuration =
    network.nodes?.find(
      (node) => node.id === "END"
    )?.ef || 0;

    console.log("PROJECT DURATION:", projectDuration);
console.log(
  "FORMATTED DURATION:",
  Number(projectDuration).toFixed(2)
);

  // =========================================
  // RENDER
  // =========================================

  return (
    <div className="network-page">

      {/* =====================================
          HEADER
          ===================================== */}

      <header className="network-header">

        <div>
          <span className="page-eyebrow">
            CPM NETWORK
          </span>

          <h1>Project Network</h1>

          <p>
            Visualize dependencies, scheduling
            calculations, and the critical path.
          </p>
        </div>

        <button
          type="button"
          className="network-back-button"
          onClick={() =>
            navigate(
              `/projects/${projectId}`
            )
          }
        >
          ← Back to Project
        </button>

      </header>

      {/* =====================================
          METRICS
          ===================================== */}

      <section className="network-metrics">

        <div className="network-metric-card">
          <span>Project Duration</span>

          <strong>{Number(projectDuration).toFixed(2)} days</strong>
        </div>

        <div className="network-metric-card">
          <span>Total Activities</span>

          <strong>
            {activityNodes.length}
          </strong>
        </div>

        <div className="network-metric-card critical">
          <span>Critical Activities</span>

          <strong>
            {criticalCount}
          </strong>
        </div>

        <div className="network-metric-card">
          <span>Critical Path</span>

          <strong>
            {criticalPath.length} activities
          </strong>
        </div>

      </section>

      {/* =====================================
          CRITICAL PATH
          ===================================== */}

      <section className="critical-path-card">

        <div>
          <span className="page-eyebrow">
            CRITICAL PATH
          </span>

          <h2>
            Activities that determine project
            completion
          </h2>

          <p>
            Activities with zero slack determine
            the minimum project duration.
          </p>
        </div>

        <div className="critical-path-list">

          {criticalPath.length > 0 ? (
            criticalPath.map(
              (activityId, index) => {

                const activity =
                  network.nodes?.find(
                    (node) =>
                      node.id === activityId
                  );

                return (
                  <div
                    className="critical-path-item"
                    key={activityId}
                  >

                    <span>
                      {index + 1}
                    </span>

                    <strong>
                      {activity?.name ||
                        activityId}
                    </strong>

                    {index <
                      criticalPath.length - 1 && (
                      <span className="critical-arrow">
                        →
                      </span>
                    )}

                  </div>
                );
              }
            )
          ) : (
            <p>
              No critical path detected.
            </p>
          )}

        </div>

      </section>

      {/* =====================================
          LEGEND
          ===================================== */}

      <section className="network-legend">

        <div className="legend-item">
          <span className="legend-line critical-line" />
          <span>
            Critical Path
          </span>
        </div>

        <div className="legend-item">
          <span className="legend-line normal-line" />
          <span>
            Normal Dependency
          </span>
        </div>

        <div className="legend-item">
          <span className="legend-node critical-node" />
          <span>
            Critical Activity
          </span>
        </div>

      </section>

      {/* =====================================
          NETWORK DIAGRAM
          ===================================== */}

      <section className="network-diagram-card">

        <div className="section-header">

          <div>
            <span className="page-eyebrow">
              ACTIVITY NETWORK
            </span>

            <h2>
              CPM Network Diagram
            </h2>

            <p>
              Red nodes and connections represent
              the critical path.
            </p>
          </div>

        </div>

        <div className="network-canvas">

          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            fitViewOptions={{
              padding: 0.2,
            }}
            attributionPosition="bottom-left"
          >

            <Background />

            <Controls />

            <MiniMap />

          </ReactFlow>

        </div>

      </section>

      {/* =====================================
          CPM ACTIVITY ANALYSIS
          ===================================== */}

      <section className="cpm-analysis-card">

        <div className="section-header">

          <div>
            <span className="page-eyebrow">
              CPM ANALYSIS
            </span>

            <h2>
              Activity Schedule Analysis
            </h2>

            <p>
              Detailed scheduling calculations for
              every project activity.
            </p>
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
              </tr>

            </thead>

            <tbody>

              {activityNodes.map(
                (node) => (

                  <tr
                    key={node.id}
                    className={
                      node.is_critical
                        ? "critical-row"
                        : ""
                    }
                  >

                    <td>

                      <div className="activity-name-cell">

                        <strong>
                          {node.name}
                        </strong>

                        {node.is_critical && (
                          <span className="critical-badge">
                            Critical
                          </span>
                        )}

                      </div>

                    </td>

                    <td>
                      {node.duration} days
                    </td>

                    <td>
                      {node.es}
                    </td>

                    <td>
                      {node.ef}
                    </td>

                    <td>
                      {node.ls}
                    </td>

                    <td>
                      {node.lf}
                    </td>

                    <td>

                      <span
                        className={
                          node.slack === 0
                            ? "slack-zero"
                            : "slack-value"
                        }
                      >
                        {node.slack}
                      </span>

                    </td>

                    <td>

                      {node.is_critical ? (
                        <span className="status-critical">
                          Critical
                        </span>
                      ) : (
                        <span className="status-normal">
                          Non-critical
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

export default Network;