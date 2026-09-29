import { useCallback, useEffect, useState } from "react";

import XaiReport from "./XaiExplanationCard";

/**
 * Loads one XAI report and renders it with consistent loading, error and
 * empty states. `fetcher` must be a stable function so the effect does not
 * re-run on every render.
 */
function XaiPanel({
  fetcher,
  projectId,
  params,
  title,
  defaultExpanded = 2,
}) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!projectId || !fetcher) {
        return;
      }
      try {
        setLoading(true);
        setError("");
        const data = await fetcher(projectId, params);
        if (!cancelled) {
          setReport(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err.response?.data?.detail ||
              "The explanation service is unavailable."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [projectId, fetcher, params, reloadToken]);

  const handleRetry = useCallback(() => {
    setReloadToken((token) => token + 1);
  }, []);

  if (loading) {
    return (
      <div className="xai-panel-status">
        <span className="xai-spinner" />
        Deriving the explanation from the schedule&hellip;
      </div>
    );
  }

  if (error) {
    return (
      <div className="xai-panel-status xai-panel-error">
        <strong>Explanation unavailable.</strong> {error}
        <button type="button" onClick={handleRetry}>
          Retry
        </button>
      </div>
    );
  }

  if (!report) {
    return null;
  }

  return (
    <div className="xai-panel">
      {title && <h2 className="xai-panel-title">{title}</h2>}
      <XaiReport report={report} defaultExpanded={defaultExpanded} />
    </div>
  );
}

export default XaiPanel;
