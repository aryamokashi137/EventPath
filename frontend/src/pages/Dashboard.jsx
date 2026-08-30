import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FolderKanban,
  Plus,
  CalendarDays,
  ArrowRight,
  Clock3,
} from "lucide-react";
import { getProjects } from "../services/projectService";

function Dashboard() {
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadProjects = async () => {
      try {
        const data = await getProjects();
        setProjects(data);
      } catch (error) {
        console.error("Error loading dashboard:", error);
      } finally {
        setLoading(false);
      }
    };

    loadProjects();
  }, []);

  const totalProjects = projects.length;

  return (
    <div className="dashboard-page">

      {/* Header */}
      <section className="dashboard-hero">
        <div>
          <span className="eyebrow">WORKSPACE OVERVIEW</span>

          <h1>Good to see you 👋</h1>

          <p>
            Plan, organize, and monitor your event projects
            from one place.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() => navigate("/projects")}
        >
          <Plus size={18} />
          New Project
        </button>
      </section>

      {/* Stats */}
      <section className="dashboard-stats">

        <div className="stat-card">
          <div className="stat-icon">
            <FolderKanban size={21} />
          </div>

          <div>
            <span>Total Projects</span>
            <strong>{loading ? "—" : totalProjects}</strong>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <Clock3 size={21} />
          </div>

          <div>
            <span>Planning Mode</span>
            <strong>CPM / PERT</strong>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <CalendarDays size={21} />
          </div>

          <div>
            <span>Schedule Analysis</span>
            <strong>Enabled</strong>
          </div>
        </div>

      </section>

      {/* Projects */}
      <section className="dashboard-section">

        <div className="section-heading">
          <div>
            <h2>Recent Projects</h2>
            <p>Your latest planning projects</p>
          </div>

          <button
            className="text-button"
            onClick={() => navigate("/projects")}
          >
            View all
            <ArrowRight size={16} />
          </button>
        </div>

        {loading ? (
          <div className="dashboard-empty">
            <p>Loading projects...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="dashboard-empty">
            <div className="empty-icon">
              <FolderKanban size={25} />
            </div>

            <h3>No projects yet</h3>

            <p>
              Create your first project and start building
              your event schedule.
            </p>

            <button
              className="primary-button"
              onClick={() => navigate("/projects")}
            >
              <Plus size={17} />
              Create Project
            </button>
          </div>
        ) : (
          <div className="dashboard-project-grid">

            {projects.slice(0, 4).map((project) => (
              <div
                className="dashboard-project-card"
                key={project.id}
                onClick={() =>
                  navigate(`/projects/${project.id}`)
                }
              >
                <div className="project-card-top">
                  <div className="project-card-icon">
                    <FolderKanban size={19} />
                  </div>

                  <span className="mode-badge">
                    {project.mode}
                  </span>
                </div>

                <h3>{project.name}</h3>

                <p>
                  {project.description ||
                    "No description available."}
                </p>

                <div className="project-card-footer">
                  <span>
                    {project.category || "GENERAL"}
                  </span>

                  <ArrowRight size={16} />
                </div>
              </div>
            ))}

          </div>
        )}

      </section>

    </div>
  );
}

export default Dashboard;