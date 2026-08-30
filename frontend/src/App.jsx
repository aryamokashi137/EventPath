
import ProjectAnalysis from "./pages/ProjectAnalysis";
import Network from "./pages/Network";
import Analytics from "./pages/Analytics";
import Schedule from "./pages/Schedule";
import Settings from "./pages/Settings";
import Profile from "./pages/Profile";
import { NavLink, Route, Routes } from "react-router-dom";
import {
  BarChart3,
  CalendarDays,
  ChevronRight,
  Crown,
  FolderKanban,
  LayoutDashboard,
  Menu,
  Settings as SettingsIcon,
  Sun,
  Moon,
  User,
  X,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useAuth } from "./context/AuthContext";

import Dashboard from "./pages/Dashboard";
import Projects from "./pages/Projects";
import ProjectDetails from "./pages/ProjectDetails";

import "./App.css";

function App() {
  const { role, toggleRole, isAdmin } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("eventpath_theme") || "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("eventpath_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  return (
    <div className="app-shell">

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={closeSidebar}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`app-sidebar ${
          sidebarOpen ? "sidebar-open" : ""
        }`}
      >
        {/* Brand */}
        <div className="sidebar-header">

          <div className="brand-mark">
            EP
          </div>

          <div className="brand-content">
            <h1>EventPath</h1>
            <span>Project Planning</span>
          </div>

          <button
            className="mobile-close-button"
            onClick={closeSidebar}
            aria-label="Close navigation"
          >
            <X size={20} />
          </button>

        </div>

        {/* Navigation */}
        <nav className="sidebar-navigation">

          <div className="navigation-label">
            WORKSPACE
          </div>

          {/* Dashboard */}
          <NavLink
            to="/"
            end
            onClick={closeSidebar}
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "sidebar-link-active" : ""
              }`
            }
          >
            <LayoutDashboard size={19} />
            <span>Dashboard</span>
          </NavLink>

          {/* Projects */}
          <NavLink
            to="/projects"
            onClick={closeSidebar}
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "sidebar-link-active" : ""
              }`
            }
          >
            <FolderKanban size={19} />
            <span>Projects</span>
          </NavLink>

          {/* Analytics */}
          <NavLink
            to="/analytics"
            onClick={closeSidebar}
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "sidebar-link-active" : ""
              }`
            }
          >
            <BarChart3 size={19} />
            <span>Analytics</span>
          </NavLink>

          <div className="navigation-label navigation-label-spaced">
            TOOLS
          </div>

          {/* Schedule */}
          <NavLink
            to="/schedule"
            onClick={closeSidebar}
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "sidebar-link-active" : ""
              }`
            }
          >
            <CalendarDays size={19} />
            <span>Schedule</span>
          </NavLink>

          {/* Settings */}
          <NavLink
            to="/settings"
            onClick={closeSidebar}
            className={({ isActive }) =>
              `sidebar-link ${
                isActive ? "sidebar-link-active" : ""
              }`
            }
          >
            <SettingsIcon size={19} />
            <span>Settings</span>
          </NavLink>

        </nav>

        {/* Sidebar footer */}
        <div className="sidebar-footer">

          <div className="sidebar-footer-card">

            <div className="footer-icon">
              <FolderKanban size={18} />
            </div>

            <div>
              <strong>EventPath</strong>
              <span>CPM & PERT Planning</span>
            </div>

          </div>

        </div>
      </aside>

      {/* Main application */}
      <main className="app-main">

        {/* Top bar */}
        <header className="topbar">

          <button
            className="mobile-menu-button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={22} />
          </button>

          <div className="topbar-breadcrumb">

            <span>EventPath</span>

            <ChevronRight size={15} />

            <span className="breadcrumb-current">
              Project Planning
            </span>

          </div>

          <div className="topbar-status">
            {/* Role Switcher Toggle */}
            <button
              type="button"
              onClick={toggleRole}
              title={`Active Role: ${role}. Click to switch to ${isAdmin ? "Standard User" : "Admin"}`}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "8px",
                border: isAdmin ? "1px solid #c7d2fe" : "1px solid #bae6fd",
                background: isAdmin ? "rgba(99, 102, 241, 0.12)" : "rgba(14, 165, 233, 0.12)",
                color: isAdmin ? "var(--accent)" : "#0284c7",
                cursor: "pointer",
                fontWeight: 700,
                fontSize: "0.8rem",
                boxShadow: "var(--shadow-sm)",
                transition: "all 0.2s ease",
              }}
            >
              {isAdmin ? (
                <>
                  <Crown size={15} color="var(--accent)" />
                  <span>Role: ADMIN</span>
                </>
              ) : (
                <>
                  <User size={15} color="#0284c7" />
                  <span>Role: USER (Read-Only)</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={toggleTheme}
              title={`Switch to ${theme === "light" ? "Dark" : "Light"} Mode`}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "8px",
                border: "1px solid var(--border-color)",
                background: "var(--bg-card)",
                color: "var(--text-primary)",
                cursor: "pointer",
                fontWeight: 600,
                fontSize: "0.8rem",
                boxShadow: "var(--shadow-sm)",
                transition: "all 0.2s ease",
              }}
            >
              {theme === "light" ? (
                <>
                  <Moon size={15} color="#6366f1" />
                  <span>Dark Mode</span>
                </>
              ) : (
                <>
                  <Sun size={15} color="#f59e0b" />
                  <span>Light Mode</span>
                </>
              )}
            </button>

            <NavLink
              to="/profile"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "4px 10px",
                borderRadius: "8px",
                background: "var(--bg-card)",
                border: "1px solid var(--border-color)",
                color: "var(--text-primary)",
                textDecoration: "none",
                fontSize: "0.85rem",
                fontWeight: 600,
              }}
            >
              <div
                style={{
                  width: "24px",
                  height: "24px",
                  borderRadius: "50%",
                  background: "#6366f1",
                  color: "#fff",
                  fontSize: "0.7rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 800,
                }}
              >
                AM
              </div>
              <span>Arya Mokashi</span>
            </NavLink>

            <span className="status-dot" style={{ marginLeft: "6px" }} />

            <span>System Ready</span>

          </div>

        </header>

        {/* Page content */}
        <div className="page-container">

          <Routes>

            {/* =====================================
                DASHBOARD
                URL: /
               ===================================== */}
            <Route
              path="/"
              element={<Dashboard />}
            />

            {/* =====================================
                PROJECTS
                URL: /projects
               ===================================== */}
            <Route
              path="/projects"
              element={<Projects />}
            />

            <Route
              path="/projects/:projectId"
              element={<ProjectDetails />}
            />

            <Route
  path="/projects/:projectId/analysis"
  element={<ProjectAnalysis />}
/>

            <Route
  path="/projects/:projectId/network"
  element={<Network />}
/>

            <Route
              path="/analytics"
              element={<Analytics />}
            />

            <Route
              path="/schedule"
              element={<Schedule />}
            />

            <Route
              path="/settings"
              element={<Settings />}
            />

            <Route
              path="/profile"
              element={<Profile />}
            />

          </Routes>

        </div>

      </main>

    </div>
  );
}

export default App;
