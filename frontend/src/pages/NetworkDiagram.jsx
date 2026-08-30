import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { getProjectNetwork } from "../services/projectService";

function NetworkDiagram() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [network, setNetwork] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  const nodes = useMemo(() => {
    if (!network?.nodes) {
      return [];
    }

    return network.nodes.map((node, index) => {
      const isCritical = node.is_critical;

      return {
        id: node.id,

        position: {
          x: (index % 3) * 300,
          y: Math.floor(index / 3) * 180,
        },

        data: {
          label: (
            <div className="network-node">
              <strong>{node.name}</strong>

              {node.id !== "START" &&
                node.id !== "END" && (
                  <>
                    <span>
                      Duration: {node.duration} days
                    </span>

                    <span>
                      ES: {node.es} | EF: {node.ef}
                    </span>

                    <span>
                      LS: {node.ls} | LF: {node.lf}
                    </span>

                    <span>
                      Slack: {node.slack}
                    </span>
                  </>
                )}
            </div>
          ),
        },

        style: {
          width: 230,

          padding: 14,

          borderRadius: 12,

          border: isCritical
            ? "2px solid #dc2626"
            : "1px solid #d1d5db",

          background: isCritical
            ? "#fef2f2"
            : "#ffffff",

          boxShadow: isCritical
            ? "0 4px 14px rgba(220, 38, 38, 0.15)"
            : "0 2px 8px rgba(15, 23, 42, 0.08)",
        },
      };
    });
  }, [network]);

  const edges = useMemo(() => {
    if (!network?.edges) {
      return [];
    }

    return network.edges.map((edge) => {
      const isCritical =
        network.critical_path?.includes(edge.from_node) &&
        network.critical_path?.includes(edge.to_node);

      return {
        id: `${edge.from_node}-${edge.to_node}`,

        source: edge.from_node,

        target: edge.to_node,

        type: "smoothstep",

        markerEnd: {
          type: MarkerType.ArrowClosed,
        },

        style: {
          stroke: isCritical
            ? "#dc2626"
            : "#94a3b8",

          strokeWidth: isCritical ? 3 : 2,
        },
      };
    });
  }, [network]);

  if (loading) {
    return (
      <div className="network-loading">
        Loading network diagram...
      </div>
    );
  }

  if (error) {
    return (
      <div className="network-error">
        <h2>Unable to load network</h2>

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

  if (!network) {
    return <p>No network data available.</p>;
  }

  return (
    <div className="network-page">

      <div className="network-header">

        <div>
          <button
            className="network-back-button"
            onClick={() =>
              navigate(`/projects/${projectId}`)
            }
          >
            ← Back to Project
          </button>

          <h1>CPM Network Diagram</h1>

          <p>
            Visualize activity dependencies,
            schedule timing, and the critical path.
          </p>
        </div>

        <div className="network-summary">

          <div>
            <strong>
              {network.nodes.length - 2}
            </strong>

            <span>Activities</span>
          </div>

          <div>
            <strong>
              {network.critical_path?.length || 0}
            </strong>

            <span>Critical Activities</span>
          </div>

          <div>
            <strong>
  {Number(
    network.nodes.find(
      (node) => node.id === "END"
    )?.ef || 0
  ).toFixed(2)}
</strong>

            <span>Project Duration</span>
          </div>

        </div>

      </div>

      <div className="network-legend">

        <div>
          <span className="legend-critical" />
          Critical Activity
        </div>

        <div>
          <span className="legend-normal" />
          Normal Activity
        </div>

      </div>

      <div className="network-canvas">

        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          minZoom={0.3}
          maxZoom={1.5}
        >
          <Background />

          <Controls />

          <MiniMap />
        </ReactFlow>

      </div>

      <section className="critical-path-panel">

        <div>
          <h2>Critical Path</h2>

          <p>
            Activities with zero slack determine
            the minimum project duration.
          </p>
        </div>

        <div className="critical-path-list">

          {network.critical_path?.map(
            (activityId, index) => {

              const activity =
                network.nodes.find(
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
                    network.critical_path.length -
                      1 && (
                    <span className="path-arrow">
                      →
                    </span>
                  )}
                </div>
              );
            }
          )}

        </div>

      </section>

    </div>
  );
}

export default NetworkDiagram;