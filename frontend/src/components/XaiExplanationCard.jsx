import { useState } from "react";
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  ChevronDown,
  Info,
  Lightbulb,
  ShieldAlert,
  Sigma,
} from "lucide-react";

const SEVERITY_META = {
  CRITICAL: { icon: ShieldAlert, label: "Critical" },
  WARNING: { icon: AlertTriangle, label: "Warning" },
  SUCCESS: { icon: CheckCircle2, label: "Clear" },
  INFO: { icon: Info, label: "Insight" },
};

const SEVERITY_ORDER = ["CRITICAL", "WARNING", "INFO", "SUCCESS"];

const PRIORITY_META = {
  HIGH: { className: "xai-action-priority-high", label: "High priority" },
  MEDIUM: { className: "xai-action-priority-medium", label: "Medium priority" },
  LOW: { className: "xai-action-priority-low", label: "Low priority" },
};

function sortCards(cards) {
  return [...cards].sort(
    (a, b) =>
      SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)
  );
}

function XaiEvidenceTable({ evidence }) {
  if (!evidence || evidence.length === 0) {
    return null;
  }

  return (
    <table className="xai-evidence-table">
      <tbody>
        {evidence.map((row) => (
          <tr key={row.label}>
            <th scope="row">{row.label}</th>
            <td>{row.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function XaiFindingCard({ card }) {
  const [showEvidence, setShowEvidence] = useState(false);
  const meta = SEVERITY_META[card.severity] || SEVERITY_META.INFO;
  const Icon = meta.icon;
  const hasDetail =
    (card.evidence && card.evidence.length > 0) ||
    (card.actions && card.actions.length > 0);

  return (
    <article className={`xai-finding xai-finding-${card.severity.toLowerCase()}`}>
      <header className="xai-finding-header">
        <span className={`xai-severity-chip xai-severity-${card.severity.toLowerCase()}`}>
          <Icon size={13} />
          {meta.label}
        </span>
        <h4>{card.title}</h4>
        <span className="xai-finding-kind">{card.kind.replace(/_/g, " ").toLowerCase()}</span>
      </header>

      <p className="xai-finding-narrative">{card.narrative}</p>

      {card.actions && card.actions.length > 0 && (
        <ul className="xai-action-list">
          {card.actions.map((action) => {
            const priority = PRIORITY_META[action.priority] || PRIORITY_META.LOW;
            return (
              <li key={action.action} className="xai-action">
                <div className="xai-action-head">
                  <Lightbulb size={14} />
                  <span className={priority.className}>{priority.label}</span>
                  {action.metric && (
                    <span className="xai-action-metric">{action.metric}</span>
                  )}
                </div>
                <p className="xai-action-text">{action.action}</p>
                <p className="xai-action-rationale">{action.rationale}</p>
              </li>
            );
          })}
        </ul>
      )}

      {hasDetail && (
        <>
          <button
            type="button"
            className="xai-evidence-toggle"
            onClick={() => setShowEvidence((open) => !open)}
            aria-expanded={showEvidence}
          >
            <Sigma size={13} />
            {showEvidence ? "Hide" : "Show"} the evidence
            <ChevronDown
              size={14}
              className={showEvidence ? "xai-chevron-open" : ""}
            />
          </button>
          {showEvidence && <XaiEvidenceTable evidence={card.evidence} />}
        </>
      )}
    </article>
  );
}

function XaiReport({ report, defaultExpanded = 2 }) {
  const [showTrace, setShowTrace] = useState(false);
  const [visibleCards, setVisibleCards] = useState(defaultExpanded);

  if (!report) {
    return null;
  }

  const cards = sortCards(report.cards || []);
  const headline = report.headline;
  const confidence = report.confidence;

  return (
    <section className={`xai-report xai-report-${(report.severity || "info").toLowerCase()}`}>
      <header className="xai-report-header">
        <div className="xai-report-heading">
          <span className="xai-report-badge">
            <Brain size={13} />
            Explainable AI
          </span>
          <h3>{report.title}</h3>
        </div>

        {headline && (
          <div className={`xai-headline xai-headline-${headline.tone || "info"}`}>
            <span>{headline.label}</span>
            <strong>{headline.value}</strong>
          </div>
        )}
      </header>

      <p className="xai-report-summary">{report.summary}</p>

      {report.narrative && report.narrative.length > 0 && (
        <ol className="xai-narrative-list">
          {report.narrative.map((sentence) => (
            <li key={sentence}>{sentence}</li>
          ))}
        </ol>
      )}

      {cards.length > 0 && (
        <div className="xai-finding-list">
          {cards.slice(0, visibleCards).map((card) => (
            <XaiFindingCard key={`${card.kind}-${card.title}`} card={card} />
          ))}
        </div>
      )}

      {cards.length > visibleCards && (
        <button
          type="button"
          className="xai-more-button"
          onClick={() => setVisibleCards((count) => count + 5)}
        >
          Show {Math.min(5, cards.length - visibleCards)} more finding
          {cards.length - visibleCards > 5 ? "s" : ""} ({cards.length} total)
        </button>
      )}

      {report.evidence_trace && report.evidence_trace.length > 0 && (
        <div className="xai-trace">
          <button
            type="button"
            className="xai-evidence-toggle"
            onClick={() => setShowTrace((open) => !open)}
            aria-expanded={showTrace}
          >
            <Sigma size={13} />
            {showTrace ? "Hide" : "Show"} how this was computed
            <ChevronDown size={14} className={showTrace ? "xai-chevron-open" : ""} />
          </button>

          {showTrace && (
            <ol className="xai-trace-list">
              {report.evidence_trace.map((step) => (
                <li key={step.step}>
                  <strong>{step.step}</strong>
                  <span className="xai-trace-method">{step.method}</span>
                  <span className="xai-trace-inputs">{step.inputs}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {confidence && (
        <p className="xai-confidence">
          Confidence: <strong>{confidence.level}</strong> — {confidence.basis}
        </p>
      )}
    </section>
  );
}

export default XaiReport;
