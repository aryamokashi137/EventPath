import { useState } from "react";
import {
  Settings as SettingsIcon,
  Sliders,
  Bell,
  Database,
  Shield,
  Save,
  CheckCircle,
  RotateCcw,
  Zap,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

function Settings() {
  const { isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState("general"); // 'general' | 'engine' | 'notifications' | 'api'
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Settings State
  const [settings, setSettings] = useState({
    defaultMode: "PERT",
    defaultTimeUnit: "DAYS",
    currency: "INR",
    mcDefaultSimulations: 1000,
    mcConfidenceLevel: 80,
    floatTolerance: 0.0,
    notifyVendorOverbooking: true,
    notifyCriticalPathVariance: true,
    notifyCrashingLimit: false,
    apiUrl: "http://127.0.0.1:8000/api/v1",
    autoSync: true,
  });

  const handleSave = (e) => {
    e.preventDefault();
    if (!isAdmin) {
      alert("Access Denied: Workspace Administrator privileges ('ADMIN' role) are required to save system settings.");
      return;
    }
    localStorage.setItem("eventpath_settings", JSON.stringify(settings));
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  const handleReset = () => {
    if (!isAdmin) {
      alert("Access Denied: Workspace Administrator privileges ('ADMIN' role) are required to reset system settings.");
      return;
    }
    const defaults = {
      defaultMode: "PERT",
      defaultTimeUnit: "DAYS",
      currency: "INR",
      mcDefaultSimulations: 1000,
      mcConfidenceLevel: 80,
      floatTolerance: 0.0,
      notifyVendorOverbooking: true,
      notifyCriticalPathVariance: true,
      notifyCrashingLimit: false,
      apiUrl: "http://127.0.0.1:8000/api/v1",
      autoSync: true,
    };
    setSettings(defaults);
    localStorage.setItem("eventpath_settings", JSON.stringify(defaults));
  };

  return (
    <div className="dashboard-page">
      {/* Hero Header */}
      <section className="dashboard-hero">
        <div>
          <span className="eyebrow">SYSTEM CONFIGURATION</span>
          <h1>Platform Settings</h1>
          <p>
            Configure default CPM/PERT engine parameters, Monte Carlo risk simulation bounds, and notification preferences.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button type="button" className="secondary-action" onClick={handleReset} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <RotateCcw size={16} /> Reset Defaults
          </button>
          <button type="button" className="primary-button" onClick={handleSave} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Save size={16} /> Save Changes
          </button>
        </div>
      </section>

      {savedSuccess && (
        <div style={{ padding: "14px 18px", borderRadius: "10px", background: "rgba(34, 197, 94, 0.15)", border: "1px solid #bbf7d0", color: "#16a34a", display: "flex", alignItems: "center", gap: "10px", fontWeight: 600 }}>
          <CheckCircle size={20} /> Settings saved successfully!
        </div>
      )}

      {/* Settings Navigation Tabs */}
      <section style={{ display: "flex", gap: "12px", borderBottom: "1px solid var(--border-color)", paddingBottom: "10px" }}>
        <button
          className={activeTab === "general" ? "filter-active" : ""}
          style={{ padding: "8px 16px", borderRadius: "8px", border: "1px solid var(--border-color)", background: activeTab === "general" ? "var(--accent)" : "var(--bg-card)", color: activeTab === "general" ? "#fff" : "var(--text-secondary)", cursor: "pointer", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}
          onClick={() => setActiveTab("general")}
        >
          <Sliders size={16} /> General Preferences
        </button>

        <button
          className={activeTab === "engine" ? "filter-active" : ""}
          style={{ padding: "8px 16px", borderRadius: "8px", border: "1px solid var(--border-color)", background: activeTab === "engine" ? "var(--accent)" : "var(--bg-card)", color: activeTab === "engine" ? "#fff" : "var(--text-secondary)", cursor: "pointer", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}
          onClick={() => setActiveTab("engine")}
        >
          <Zap size={16} /> Scheduling Engine (CPM/PERT)
        </button>

        <button
          className={activeTab === "notifications" ? "filter-active" : ""}
          style={{ padding: "8px 16px", borderRadius: "8px", border: "1px solid var(--border-color)", background: activeTab === "notifications" ? "var(--accent)" : "var(--bg-card)", color: activeTab === "notifications" ? "#fff" : "var(--text-secondary)", cursor: "pointer", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}
          onClick={() => setActiveTab("notifications")}
        >
          <Bell size={16} /> Vendor Alerts
        </button>

        <button
          className={activeTab === "api" ? "filter-active" : ""}
          style={{ padding: "8px 16px", borderRadius: "8px", border: "1px solid var(--border-color)", background: activeTab === "api" ? "var(--accent)" : "var(--bg-card)", color: activeTab === "api" ? "#fff" : "var(--text-secondary)", cursor: "pointer", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}
          onClick={() => setActiveTab("api")}
        >
          <Database size={16} /> API Endpoint & Sync
        </button>
      </section>

      {/* Settings Content Box */}
      <form onSubmit={handleSave} className="analysis-panel" style={{ background: "var(--bg-card)", padding: "24px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
        {/* TAB 1: GENERAL PREFERENCES */}
        {activeTab === "general" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h3 style={{ color: "var(--text-primary)" }}>Workspace & Regional Preferences</h3>

            <div className="form-group">
              <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Default Project Planning Mode</label>
              <select
                value={settings.defaultMode}
                onChange={(e) => setSettings({ ...settings, defaultMode: e.target.value })}
                style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", maxWidth: "400px" }}
              >
                <option value="PERT">PERT (Probabilistic 3-Point Estimate)</option>
                <option value="CPM">CPM (Deterministic Single Estimate)</option>
              </select>
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: "4px 0 0 0" }}>
                Default mode selected when initializing new blank projects.
              </p>
            </div>

            <div className="form-group">
              <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Default Duration Unit</label>
              <select
                value={settings.defaultTimeUnit}
                onChange={(e) => setSettings({ ...settings, defaultTimeUnit: e.target.value })}
                style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", maxWidth: "400px" }}
              >
                <option value="DAYS">Days (Standard Event Planning)</option>
                <option value="WEEKS">Weeks</option>
                <option value="HOURS">Hours (Single-Day Execution)</option>
              </select>
            </div>

            <div className="form-group">
              <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Currency Symbol</label>
              <select
                value={settings.currency}
                onChange={(e) => setSettings({ ...settings, currency: e.target.value })}
                style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", maxWidth: "400px" }}
              >
                <option value="INR">₹ INR (Indian Rupee)</option>
                <option value="USD">$ USD (US Dollar)</option>
                <option value="EUR">€ EUR (Euro)</option>
              </select>
            </div>
          </div>
        )}

        {/* TAB 2: SCHEDULING ENGINE */}
        {activeTab === "engine" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h3 style={{ color: "var(--text-primary)" }}>Monte Carlo PERT & Critical Path Parameters</h3>

            <div className="form-group">
              <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Monte Carlo Default Simulation Runs</label>
              <input
                type="number"
                min="100"
                max="10000"
                step="100"
                value={settings.mcDefaultSimulations}
                onChange={(e) => setSettings({ ...settings, mcDefaultSimulations: Number(e.target.value) })}
                style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", maxWidth: "400px" }}
              />
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: "4px 0 0 0" }}>
                Higher iterations yield precise S-Curves and criticality indices (recommended: 1,000–5,000 runs).
              </p>
            </div>

            <div className="form-group">
              <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Target Probability Confidence Threshold (%)</label>
              <input
                type="number"
                min="50"
                max="99"
                value={settings.mcConfidenceLevel}
                onChange={(e) => setSettings({ ...settings, mcConfidenceLevel: Number(e.target.value) })}
                style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", maxWidth: "400px" }}
              />
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: "4px 0 0 0" }}>
                Default target percentile used for project deadline risk assessment (P80 means 80% confidence).
              </p>
            </div>

            <div className="form-group">
              <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Critical Path Float Slack Tolerance (Days)</label>
              <input
                type="number"
                min="0"
                max="5"
                step="0.1"
                value={settings.floatTolerance}
                onChange={(e) => setSettings({ ...settings, floatTolerance: Number(e.target.value) })}
                style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", maxWidth: "400px" }}
              />
              <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: "4px 0 0 0" }}>
                Activities with Total Float ≤ this value will be classified as critical bottlenecks.
              </p>
            </div>
          </div>
        )}

        {/* TAB 3: NOTIFICATIONS */}
        {activeTab === "notifications" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h3 style={{ color: "var(--text-primary)" }}>Vendor & Schedule Conflict Alerts (Gap 5)</h3>

            <label style={{ display: "flex", alignItems: "center", gap: "12px", cursor: "pointer", color: "var(--text-primary)" }}>
              <input
                type="checkbox"
                checked={settings.notifyVendorOverbooking}
                onChange={(e) => setSettings({ ...settings, notifyVendorOverbooking: e.target.checked })}
                style={{ width: "18px", height: "18px" }}
              />
              <div>
                <strong>Vendor Overbooking & Window Violation Alerts</strong>
                <p style={{ margin: "2px 0 0 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  Notify when a vendor partner is assigned to overlapping activities or outside availability windows.
                </p>
              </div>
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: "12px", cursor: "pointer", color: "var(--text-primary)" }}>
              <input
                type="checkbox"
                checked={settings.notifyCriticalPathVariance}
                onChange={(e) => setSettings({ ...settings, notifyCriticalPathVariance: e.target.checked })}
                style={{ width: "18px", height: "18px" }}
              />
              <div>
                <strong>Critical Path Variance Warnings</strong>
                <p style={{ margin: "2px 0 0 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  Warn if a critical path activity duration increases, extending project completion.
                </p>
              </div>
            </label>
          </div>
        )}

        {/* TAB 4: API ENDPOINT */}
        {activeTab === "api" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h3 style={{ color: "var(--text-primary)" }}>Backend Service Configuration</h3>

            <div className="form-group">
              <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>FastAPI Backend Endpoint Base URL</label>
              <input
                type="text"
                value={settings.apiUrl}
                onChange={(e) => setSettings({ ...settings, apiUrl: e.target.value })}
                style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", width: "100%", maxWidth: "500px" }}
              />
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: "12px", cursor: "pointer", color: "var(--text-primary)" }}>
              <input
                type="checkbox"
                checked={settings.autoSync}
                onChange={(e) => setSettings({ ...settings, autoSync: e.target.checked })}
                style={{ width: "18px", height: "18px" }}
              />
              <div>
                <strong>Enable Automatic Local Network Cache & Polling</strong>
                <p style={{ margin: "2px 0 0 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                  Synchronize DAG changes and float calculations in the background.
                </p>
              </div>
            </label>
          </div>
        )}

        <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid var(--border-color)", display: "flex", justifyContent: "flex-end" }}>
          <button type="submit" className="primary-button" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Save size={16} /> Save Settings
          </button>
        </div>
      </form>
    </div>
  );
}

export default Settings;
