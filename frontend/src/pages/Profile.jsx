import { useState } from "react";
import {
  User,
  Mail,
  Briefcase,
  ShieldCheck,
  Building,
  Key,
  CheckCircle,
  Save,
  Award,
  Calendar,
  Crown,
  Shield,
  Check,
  X as XIcon,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

function Profile() {
  const { role, setRole, toggleRole, isAdmin } = useAuth();
  const [savedSuccess, setSavedSuccess] = useState(false);

  const [profile, setProfile] = useState({
    fullName: "Arya Mokashi",
    email: "aryamokashi137@eventpath.ai",
    role: isAdmin ? "Lead Workspace Administrator" : "Senior Event Planner",
    company: "EventPath Global Operations",
    bio: "CPM & PERT scheduling specialist managing complex multi-vendor event logistics, trade shows, and ceremony workflows.",
    timezone: "Asia/Kolkata (GMT+5:30)",
  });

  const [passwords, setPasswords] = useState({
    current: "",
    newPass: "",
    confirm: "",
  });

  const [passError, setPassError] = useState("");
  const [passSuccess, setPassSuccess] = useState(false);

  const handleProfileSave = (e) => {
    e.preventDefault();
    localStorage.setItem("eventpath_user_profile", JSON.stringify(profile));
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  const handlePasswordUpdate = (e) => {
    e.preventDefault();
    if (!passwords.current) {
      setPassError("Please enter your current password.");
      return;
    }
    if (passwords.newPass.length < 6) {
      setPassError("New password must be at least 6 characters.");
      return;
    }
    if (passwords.newPass !== passwords.confirm) {
      setPassError("New passwords do not match.");
      return;
    }

    setPassError("");
    setPassSuccess(true);
    setPasswords({ current: "", newPass: "", confirm: "" });
    setTimeout(() => setPassSuccess(false), 3000);
  };

  return (
    <div className="dashboard-page">
      {/* Hero Header */}
      <section className="dashboard-hero">
        <div>
          <span className="eyebrow">USER PROFILE & ROLE-BASED ACCESS CONTROL (RBAC)</span>
          <h1>Account & Access Management</h1>
          <p>
            Manage personal credentials, workspace security, and switch between Administrator and Team Member roles.
          </p>
        </div>
      </section>

      {savedSuccess && (
        <div style={{ padding: "14px 18px", borderRadius: "10px", background: "rgba(34, 197, 94, 0.15)", border: "1px solid #bbf7d0", color: "#16a34a", display: "flex", alignItems: "center", gap: "10px", fontWeight: 600 }}>
          <CheckCircle size={20} /> Profile details saved successfully!
        </div>
      )}

      {/* Grid Layout: Profile Card & Forms */}
      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: "24px" }}>
        {/* Left Column: User Badge Card & Role Switcher */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div className="analysis-panel" style={{ background: "var(--bg-card)", padding: "24px", borderRadius: "12px", border: "1px solid var(--border-color)", textAlign: "center", boxShadow: "var(--shadow-md)" }}>
            <div
              style={{
                width: "90px",
                height: "90px",
                borderRadius: "50%",
                background: isAdmin ? "linear-gradient(135deg, #6366f1, #4f46e5)" : "linear-gradient(135deg, #0284c7, #0369a1)",
                color: "#ffffff",
                fontSize: "2.2rem",
                fontWeight: 800,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 16px auto",
                boxShadow: isAdmin ? "0 4px 12px rgba(99, 102, 241, 0.3)" : "0 4px 12px rgba(2, 132, 199, 0.3)"
              }}
            >
              AM
            </div>

            <h2 style={{ margin: "0 0 4px 0", fontSize: "1.25rem", color: "var(--text-primary)" }}>{profile.fullName}</h2>
            <p style={{ margin: "0 0 14px 0", color: "var(--text-secondary)", fontSize: "0.875rem" }}>{profile.role}</p>

            <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "6px 12px", borderRadius: "20px", background: isAdmin ? "rgba(99, 102, 241, 0.12)" : "rgba(2, 132, 199, 0.12)", color: isAdmin ? "var(--accent)" : "#0284c7", fontWeight: 700, fontSize: "0.8rem" }}>
              {isAdmin ? <Crown size={15} /> : <User size={15} />}
              <span>{isAdmin ? "👑 Workspace Administrator" : "👤 Standard Team Member"}</span>
            </div>

            <div style={{ marginTop: "20px", paddingTop: "16px", borderTop: "1px solid var(--border-color)", textAlign: "left", display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Mail size={15} color="var(--accent)" /> {profile.email}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Building size={15} color="var(--accent)" /> {profile.company}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Calendar size={15} color="var(--accent)" /> Member since Aug 2026
              </div>
            </div>
          </div>

          {/* Role Switching Panel */}
          <div className="analysis-panel" style={{ background: "var(--bg-card)", padding: "20px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
            <h4 style={{ margin: "0 0 12px 0", fontSize: "0.95rem", color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
              <ShieldCheck size={18} color="var(--accent)" /> Role Switcher Control
            </h4>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)", margin: "0 0 14px 0" }}>
              Switch active role to test access permissions enforced across frontend views and backend REST APIs (`X-User-Role`).
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <button
                type="button"
                onClick={() => setRole("ADMIN")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: role === "ADMIN" ? "2px solid var(--accent)" : "1px solid var(--border-color)",
                  background: role === "ADMIN" ? "var(--accent-light)" : "var(--bg-main)",
                  color: "var(--text-primary)",
                  fontWeight: 600,
                  cursor: "pointer"
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Crown size={16} color="var(--accent)" /> Admin (Full Access)
                </span>
                {role === "ADMIN" && <Check size={16} color="var(--accent)" />}
              </button>

              <button
                type="button"
                onClick={() => setRole("USER")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: role === "USER" ? "2px solid #0284c7" : "1px solid var(--border-color)",
                  background: role === "USER" ? "rgba(14, 165, 233, 0.12)" : "var(--bg-main)",
                  color: "var(--text-primary)",
                  fontWeight: 600,
                  cursor: "pointer"
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <User size={16} color="#0284c7" /> User (Read-Only)
                </span>
                {role === "USER" && <Check size={16} color="#0284c7" />}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: RBAC Permission Matrix & Edit Forms */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* RBAC Permission Matrix */}
          <div className="analysis-panel" style={{ background: "var(--bg-card)", padding: "24px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
            <h3 style={{ margin: "0 0 6px 0", fontSize: "1.1rem", color: "var(--text-primary)" }}>Role Permission Matrix</h3>
            <p style={{ margin: "0 0 16px 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Overview of authorized capabilities separated by Admin and User roles.
            </p>

            <table className="analysis-table" style={{ width: "100%" }}>
              <thead>
                <tr>
                  <th>Capability / Feature</th>
                  <th>👑 Workspace Admin</th>
                  <th>👤 Team Member (User)</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>View Projects, Timelines & Network Graphs</strong></td>
                  <td><span style={{ color: "#16a34a", fontWeight: 700 }}>✓ Allowed</span></td>
                  <td><span style={{ color: "#16a34a", fontWeight: 700 }}>✓ Allowed</span></td>
                </tr>
                <tr>
                  <td><strong>Create & Delete Projects</strong></td>
                  <td><span style={{ color: "#16a34a", fontWeight: 700 }}>✓ Full Control</span></td>
                  <td><span style={{ color: "#ef4444", fontWeight: 700 }}>✕ Restricted (403)</span></td>
                </tr>
                <tr>
                  <td><strong>Add, Edit & Delete Project Activities</strong></td>
                  <td><span style={{ color: "#16a34a", fontWeight: 700 }}>✓ Full Control</span></td>
                  <td><span style={{ color: "#ef4444", fontWeight: 700 }}>✕ Restricted (403)</span></td>
                </tr>
                <tr>
                  <td><strong>Schedule Crashing Optimization (Gap 2 & 5)</strong></td>
                  <td><span style={{ color: "#16a34a", fontWeight: 700 }}>✓ Full Control</span></td>
                  <td><span style={{ color: "#ef4444", fontWeight: 700 }}>✕ Restricted (403)</span></td>
                </tr>
                <tr>
                  <td><strong>Run Monte Carlo & What-If Simulations</strong></td>
                  <td><span style={{ color: "#16a34a", fontWeight: 700 }}>✓ Allowed</span></td>
                  <td><span style={{ color: "#16a34a", fontWeight: 700 }}>✓ Allowed</span></td>
                </tr>
                <tr>
                  <td><strong>Modify System Engine Settings</strong></td>
                  <td><span style={{ color: "#16a34a", fontWeight: 700 }}>✓ Full Control</span></td>
                  <td><span style={{ color: "#ef4444", fontWeight: 700 }}>✕ Restricted</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Form 1: Personal Details */}
          <form onSubmit={handleProfileSave} className="analysis-panel" style={{ background: "var(--bg-card)", padding: "24px", borderRadius: "12px", border: "1px solid var(--border-color)", boxShadow: "var(--shadow-md)" }}>
            <h3 style={{ margin: "0 0 16px 0", fontSize: "1.1rem", color: "var(--text-primary)" }}>Personal Information</h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
              <div className="form-group">
                <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Full Name</label>
                <input
                  type="text"
                  value={profile.fullName}
                  onChange={(e) => setProfile({ ...profile, fullName: e.target.value })}
                  style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", width: "100%" }}
                />
              </div>

              <div className="form-group">
                <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Email Address</label>
                <input
                  type="email"
                  value={profile.email}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                  style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", width: "100%" }}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
              <div className="form-group">
                <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Job Title / Role</label>
                <input
                  type="text"
                  value={profile.role}
                  onChange={(e) => setProfile({ ...profile, role: e.target.value })}
                  style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", width: "100%" }}
                />
              </div>

              <div className="form-group">
                <label style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Company / Organization</label>
                <input
                  type="text"
                  value={profile.company}
                  onChange={(e) => setProfile({ ...profile, company: e.target.value })}
                  style={{ padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)", background: "var(--bg-main)", color: "var(--text-primary)", width: "100%" }}
                />
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button type="submit" className="primary-button" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Save size={16} /> Save Profile
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Profile;
