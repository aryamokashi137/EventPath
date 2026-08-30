import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CalendarDays,
  FolderKanban,
  LayoutGrid,
  Plus,
  Search,
  Target,
  Trash2,
  X,
} from "lucide-react";

import {
  createProject,
  deleteProject,
  getProjects,
} from "../services/projectService";

import "./Projects.css";

function Projects() {
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [search, setSearch] = useState("");
  const [modeFilter, setModeFilter] = useState("ALL");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const [form, setForm] = useState({
    name: "",
    description: "",
    category: "GENERAL",
    mode: "CPM",
    start_date: "",
    target_completion_date: "",
  });

  const [loading, setLoading] = useState(true);
const [creating, setCreating] = useState(false);
const [deleting, setDeleting] = useState(null);
const [error, setError] = useState("");

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getProjects();
      setProjects(data);
    } catch (err) {
      console.error("Error loading projects:", err);
      setError("Unable to load projects.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const filteredProjects = useMemo(() => {
    return projects.filter((project) => {
      const matchesSearch =
        project.name
          ?.toLowerCase()
          .includes(search.toLowerCase()) ||
        project.category
          ?.toLowerCase()
          .includes(search.toLowerCase());

      const matchesMode =
        modeFilter === "ALL" || project.mode === modeFilter;

      return matchesSearch && matchesMode;
    });
  }, [projects, search, modeFilter]);

  const cpmCount = projects.filter(
    (project) => project.mode === "CPM"
  ).length;

  const pertCount = projects.filter(
    (project) => project.mode === "PERT"
  ).length;

  const handleCreateProject = async (event) => {
    event.preventDefault();

    if (!form.name.trim()) {
      setError("Project name is required.");
      return;
    }

    try {
      setCreating(true);
      setError("");


      const project = await createProject({
        name: form.name.trim(),
        description:
          form.description.trim() ||
          "EventPath project",
        category: form.category || "GENERAL",
        mode: form.mode,
        start_date: form.start_date || null,
        target_completion_date:
          form.target_completion_date || null,
      });

      setProjects((current) => [project, ...current]);

      setForm({
        name: "",
        description: "",
        category: "GENERAL",
        mode: "CPM",
        start_date: "",
        target_completion_date: "",
      });

      setShowCreateModal(false);
    } catch (err) {
      console.error("Error creating project:", err);

      setError(
        err.response?.data?.detail ||
          "Failed to create project."
      );
    } finally {
      setCreating(false);
    }
  };

    const handleDeleteProject = async (project) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${project.name}"?\n\n` +
        "This will also delete all activities associated with this project."
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeleting(project.id);
      setError("");

      await deleteProject(project.id);

      setProjects((current) =>
        current.filter((item) => item.id !== project.id)
      );
    } catch (err) {
      console.error("Error deleting project:", err);

      setError(
        err.response?.data?.detail ||
          "Failed to delete project."
      );
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="projects-page">
      {/* Header */}
      <section className="projects-hero">
        <div>
          <div className="eyebrow">
            <FolderKanban size={15} />
            PROJECT WORKSPACE
          </div>

          <h1>Projects</h1>

          <p>
            Plan, schedule, analyze, and optimize your
            event projects from one workspace.
          </p>
        </div>

        <button
          className="primary-action"
          onClick={() => {
            setError("");
            setShowCreateModal(true);
          }}
        >
          <Plus size={18} />
          New Project
        </button>
      </section>

      {/* Statistics */}
      <section className="project-stat-grid">
        <div className="project-stat-card">
          <div className="stat-icon">
            <FolderKanban size={19} />
          </div>

          <div>
            <span>Total Projects</span>
            <strong>{projects.length}</strong>
          </div>
        </div>

        <div className="project-stat-card">
          <div className="stat-icon">
            <LayoutGrid size={19} />
          </div>

          <div>
            <span>CPM Projects</span>
            <strong>{cpmCount}</strong>
          </div>
        </div>

        <div className="project-stat-card">
          <div className="stat-icon">
            <Target size={19} />
          </div>

          <div>
            <span>PERT Projects</span>
            <strong>{pertCount}</strong>
          </div>
        </div>

        <div className="project-stat-card">
          <div className="stat-icon">
            <CalendarDays size={19} />
          </div>

          <div>
            <span>Planning Engine</span>
            <strong className="ready-text">Ready</strong>
          </div>
        </div>
      </section>

      {/* Error */}
      {error && (
        <div className="projects-error">
          {error}
        </div>
      )}

      {/* Project list */}
      <section className="projects-content">
        <div className="projects-section-heading">
          <div>
            <h2>Your Projects</h2>
            <p>
              {filteredProjects.length} project
              {filteredProjects.length === 1 ? "" : "s"}{" "}
              available
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="projects-toolbar">
          <div className="search-box">
            <Search size={17} />

            <input
              type="text"
              placeholder="Search projects..."
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
            />

            {search && (
              <button
                onClick={() => setSearch("")}
                aria-label="Clear search"
              >
                <X size={15} />
              </button>
            )}
          </div>

          <div className="mode-filter">
            {["ALL", "CPM", "PERT"].map((mode) => (
              <button
                key={mode}
                className={
                  modeFilter === mode
                    ? "filter-active"
                    : ""
                }
                onClick={() => setModeFilter(mode)}
              >
                {mode === "ALL" ? "All" : mode}
              </button>
            ))}
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="projects-loading">
            <div className="loading-spinner" />
            <p>Loading projects...</p>
          </div>
        )}

        {/* Empty */}
        {!loading && filteredProjects.length === 0 && (
          <div className="projects-empty">
            <div className="empty-icon">
              <FolderKanban size={28} />
            </div>

            <h3>
              {projects.length === 0
                ? "No projects yet"
                : "No matching projects"}
            </h3>

            <p>
              {projects.length === 0
                ? "Create your first project to start building an optimized event schedule."
                : "Try changing your search or filter."}
            </p>

            {projects.length === 0 && (
              <button
                className="primary-action"
                onClick={() =>
                  setShowCreateModal(true)
                }
              >
                <Plus size={17} />
                Create Project
              </button>
            )}
          </div>
        )}

        {/* Cards */}
        {!loading && filteredProjects.length > 0 && (
          <div className="projects-grid">
            {filteredProjects.map((project) => (
              <article
                className="project-card-new"
                key={project.id}
              >
                <div className="project-card-top">
                  <div className="project-type-icon">
                    <FolderKanban size={20} />
                  </div>

                  <span
                    className={`mode-badge ${
                      project.mode === "PERT"
                        ? "mode-pert"
                        : "mode-cpm"
                    }`}
                  >
                    {project.mode}
                  </span>
                </div>

                <h3>{project.name}</h3>

                <p className="project-description">
                  {project.description ||
                    "No description available."}
                </p>

                <div className="project-meta">
                  <span>
                    <LayoutGrid size={14} />
                    {project.category ||
                      "GENERAL"}
                  </span>

                  <span>
                    <CalendarDays size={14} />
                    {project.target_completion_date ||
                      "No target date"}
                  </span>
                </div>

              <div className="project-card-actions">
  <button
    className="project-open-button"
    onClick={() =>
      navigate(`/projects/${project.id}`)
    }
  >
    Open Workspace
    <ArrowRight size={16} />
  </button>

  <button
    className="project-delete-button"
    onClick={() => handleDeleteProject(project)}
    disabled={deleting === project.id}
    aria-label={`Delete ${project.name}`}
    title="Delete project"
  >
    <Trash2 size={17} />
    {deleting === project.id ? "Deleting..." : "Delete"}
  </button>
</div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Create modal */}
      {showCreateModal && (
        <div
          className="modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setShowCreateModal(false);
            }
          }}
        >
          <div className="project-modal">
            <div className="modal-header">
              <div>
                <span className="modal-eyebrow">
                  NEW PROJECT
                </span>

                <h2>Create Project</h2>

                <p>
                  Set up the basic planning information.
                </p>
              </div>

              <button
                className="modal-close"
                onClick={() =>
                  setShowCreateModal(false)
                }
                aria-label="Close"
              >
                <X size={19} />
              </button>
            </div>

            <form onSubmit={handleCreateProject}>
              <div className="form-group">
                <label>Project Name *</label>

                <input
                  autoFocus
                  value={form.name}
                  placeholder="e.g. Annual Conference"
                  onChange={(event) =>
                    setForm({
                      ...form,
                      name: event.target.value,
                    })
                  }
                />
              </div>

              <div className="form-group">
                <label>Description</label>

                <textarea
                  rows="3"
                  value={form.description}
                  placeholder="Briefly describe the project..."
                  onChange={(event) =>
                    setForm({
                      ...form,
                      description:
                        event.target.value,
                    })
                  }
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Planning Mode</label>

                  <select
                    value={form.mode}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        mode: event.target.value,
                      })
                    }
                  >
                    <option value="CPM">CPM</option>
                    <option value="PERT">PERT</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Category</label>

                  <input
                    value={form.category}
                    placeholder="GENERAL"
                    onChange={(event) =>
                      setForm({
                        ...form,
                        category:
                          event.target.value,
                      })
                    }
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Start Date</label>

                  <input
                    type="date"
                    value={form.start_date}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        start_date:
                          event.target.value,
                      })
                    }
                  />
                </div>

                <div className="form-group">
                  <label>Target Completion</label>

                  <input
                    type="date"
                    value={
                      form.target_completion_date
                    }
                    onChange={(event) =>
                      setForm({
                        ...form,
                        target_completion_date:
                          event.target.value,
                      })
                    }
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() =>
                    setShowCreateModal(false)
                  }
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="primary-action"
                  disabled={creating}
                >
                  {creating
                    ? "Creating..."
                    : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Projects;