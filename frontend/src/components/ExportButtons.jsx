import { useState } from "react";
import {
  FileText,
  FileSpreadsheet,
  Printer,
  Download,
  Sparkles,
  ChevronDown,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import {
  exportPageToPDF,
  downloadBackendCSV,
  downloadBackendPDF,
} from "../utils/exportUtils";

/**
 * Reusable Export Buttons Component for EventPath pages.
 * Supports:
 * 1. UI Replica PDF Export (captures active page DOM elements visually)
 * 2. Backend PDF Report Export (server-generated ReportLab document)
 * 3. CSV Export (backend formatted CSV file)
 * 4. Browser Native Print / PDF
 */
export default function ExportButtons({
  projectId,
  projectName = "Report",
  targetElementId = "page-export-container",
  customFilename,
  className = "",
  style = {},
}) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [loadingType, setLoadingType] = useState(null); // 'ui-pdf' | 'backend-pdf' | 'csv'
  const [successType, setSuccessType] = useState(null);

  const safeFilename = customFilename || `EventPath_${projectName.replace(/[^a-zA-Z0-9]/g, "_")}`;

  const handleExportUIPDF = async () => {
    try {
      setLoadingType("ui-pdf");
      setDropdownOpen(false);
      await exportPageToPDF(targetElementId, `${safeFilename}_UI_Replica.pdf`);
      setSuccessType("ui-pdf");
      setTimeout(() => setSuccessType(null), 2500);
    } catch (err) {
      console.error("UI PDF Export Error:", err);
      alert(`PDF Export Failed: ${err.message}`);
    } finally {
      setLoadingType(null);
    }
  };

  const handleBackendCSV = async () => {
    if (!projectId) {
      alert("No active project ID provided for CSV export.");
      return;
    }
    try {
      setLoadingType("csv");
      setDropdownOpen(false);
      await downloadBackendCSV(projectId, projectName);
      setSuccessType("csv");
      setTimeout(() => setSuccessType(null), 2500);
    } catch (err) {
      console.error("CSV Export Error:", err);
      alert("Failed to download CSV report.");
    } finally {
      setLoadingType(null);
    }
  };

  const handleBackendPDF = async () => {
    if (!projectId) {
      alert("No active project ID provided for PDF report export.");
      return;
    }
    try {
      setLoadingType("backend-pdf");
      setDropdownOpen(false);
      await downloadBackendPDF(projectId, projectName);
      setSuccessType("backend-pdf");
      setTimeout(() => setSuccessType(null), 2500);
    } catch (err) {
      console.error("Backend PDF Export Error:", err);
      alert("Failed to download Server PDF report.");
    } finally {
      setLoadingType(null);
    }
  };

  const handlePrintPage = () => {
    setDropdownOpen(false);
    window.print();
  };

  return (
    <div
      className={`export-buttons-wrapper ${className}`}
      style={{ position: "relative", display: "inline-flex", gap: "8px", ...style }}
    >
      {/* Primary Action Button: Export Page PDF (UI Replica) */}
      <button
        type="button"
        onClick={handleExportUIPDF}
        disabled={loadingType !== null}
        className="btn-export-primary"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          padding: "8px 16px",
          borderRadius: "8px",
          background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
          color: "#ffffff",
          fontWeight: 600,
          fontSize: "0.875rem",
          border: "none",
          cursor: loadingType !== null ? "not-allowed" : "pointer",
          boxShadow: "0 4px 12px rgba(99, 102, 241, 0.25)",
          transition: "all 0.2s ease",
        }}
        title="Export exact visual replica of current page view as PDF"
      >
        {loadingType === "ui-pdf" ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            <span>Generating PDF...</span>
          </>
        ) : successType === "ui-pdf" ? (
          <>
            <CheckCircle2 size={16} color="#86efac" />
            <span>PDF Exported!</span>
          </>
        ) : (
          <>
            <Sparkles size={16} />
            <span>Export Page PDF</span>
          </>
        )}
      </button>

      {/* CSV Quick Button (If projectId available) */}
      {projectId && (
        <button
          type="button"
          onClick={handleBackendCSV}
          disabled={loadingType !== null}
          className="btn-export-secondary"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            padding: "8px 14px",
            borderRadius: "8px",
            background: "var(--bg-card, #ffffff)",
            color: "var(--text-primary, #0f172a)",
            fontWeight: 600,
            fontSize: "0.875rem",
            border: "1px solid var(--border-color, #e2e8f0)",
            cursor: loadingType !== null ? "not-allowed" : "pointer",
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
            transition: "all 0.2s ease",
          }}
          title="Download schedule & float analysis as CSV"
        >
          {loadingType === "csv" ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <FileSpreadsheet size={16} color="#10b981" />
          )}
          <span>Export CSV</span>
        </button>
      )}

      {/* Dropdown Menu Toggle for More Options */}
      <div style={{ position: "relative" }}>
        <button
          type="button"
          onClick={() => setDropdownOpen((prev) => !prev)}
          className="btn-export-dropdown-toggle"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "8px 10px",
            borderRadius: "8px",
            background: "var(--bg-card, #ffffff)",
            color: "var(--text-primary, #0f172a)",
            border: "1px solid var(--border-color, #e2e8f0)",
            cursor: "pointer",
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
          title="More export formats & print options"
        >
          <ChevronDown size={16} />
        </button>

        {dropdownOpen && (
          <div
            className="export-dropdown-menu"
            style={{
              position: "absolute",
              right: 0,
              top: "calc(100% + 6px)",
              width: "230px",
              background: "var(--bg-card, #ffffff)",
              border: "1px solid var(--border-color, #e2e8f0)",
              borderRadius: "10px",
              boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.15)",
              padding: "6px",
              zIndex: 9999,
              display: "flex",
              flexDirection: "column",
              gap: "4px",
            }}
          >
            {/* 1. Page Look-a-like PDF */}
            <button
              type="button"
              onClick={handleExportUIPDF}
              className="dropdown-item"
              style={dropdownItemStyle}
            >
              <Sparkles size={16} color="#6366f1" />
              <div style={{ textAlign: "left" }}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>Export Page PDF</div>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Exact UI visual replicate</div>
              </div>
            </button>

            {/* 2. Backend Report PDF */}
            {projectId && (
              <button
                type="button"
                onClick={handleBackendPDF}
                className="dropdown-item"
                style={dropdownItemStyle}
              >
                <FileText size={16} color="#0284c7" />
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>Server PDF Report</div>
                  <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Formal ReportLab document</div>
                </div>
              </button>
            )}

            {/* 3. CSV File Download */}
            {projectId && (
              <button
                type="button"
                onClick={handleBackendCSV}
                className="dropdown-item"
                style={dropdownItemStyle}
              >
                <FileSpreadsheet size={16} color="#10b981" />
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>Export CSV Data</div>
                  <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Spreadsheet raw metrics</div>
                </div>
              </button>
            )}

            <div style={{ height: "1px", background: "var(--border-color, #e2e8f0)", margin: "4px 0" }} />

            {/* 4. Native Browser Print */}
            <button
              type="button"
              onClick={handlePrintPage}
              className="dropdown-item"
              style={dropdownItemStyle}
            >
              <Printer size={16} color="#64748b" />
              <div style={{ textAlign: "left" }}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem" }}>Print / Native PDF</div>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Browser system print dialog</div>
              </div>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

const dropdownItemStyle = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "8px 10px",
  borderRadius: "6px",
  border: "none",
  background: "transparent",
  color: "var(--text-primary, #0f172a)",
  cursor: "pointer",
  width: "100%",
  transition: "background 0.15s ease",
};
