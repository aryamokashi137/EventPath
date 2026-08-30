
import NetworkDiagram from "./pages/NetworkDiagram";
import ProjectAnalysis from "./pages/ProjectAnalysis";
import Network from "./pages/Network";
import { NavLink, Route, Routes } from "react-router-dom";
import {
  BarChart3,
  CalendarDays,
  ChevronRight,
  FolderKanban,
  LayoutDashboard,
  Menu,
  Settings,
  X,
} from "lucide-react";
import { useState } from "react";

import Dashboard from "./pages/Dashboard";
import Projects from "./pages/Projects";
import ProjectDetails from "./pages/ProjectDetails";

import "./App.css";

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

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
          <button
            type="button"
            className="sidebar-link sidebar-link-button"
          >
            <CalendarDays size={19} />
            <span>Schedule</span>

            <span className="coming-soon-badge">
              Soon
            </span>
          </button>

          {/* Settings */}
          <button
            type="button"
            className="sidebar-link sidebar-link-button"
          >
            <Settings size={19} />
            <span>Settings</span>

            <span className="coming-soon-badge">
              Soon
            </span>
          </button>

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

            <span className="status-dot" />

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
  path="/projects/:projectId/network"
  element={<NetworkDiagram />}
/>
            {}
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

            {}
            <Route
              path="/analytics"
              element={
                <div className="placeholder-page">

                  <div className="placeholder-icon">
                    <BarChart3 size={30} />
                  </div>

                  <h1>Analytics</h1>

                  <p>
                    Project analytics and schedule
                    insights will appear here.
                  </p>

                </div>
              }
            />

          </Routes>

        </div>

      </main>

    </div>
  );
}

export default App;
