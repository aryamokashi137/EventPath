import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getProject } from "../services/projectService";

function ProjectDashboard() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadProject = async () => {
      try {
        setLoading(true);
        setError("");

        const data = await getProject(projectId);
        setProject(data);
      } catch (error) {
        console.error("Error loading project:", error);
        setError("Failed to load project.");
      } finally {
        setLoading(false);
      }
    };

    loadProject();
  }, [projectId]);

  if (loading) {
    return <p>Loading project...</p>;
  }

  if (error) {
    return (
      <div>
        <p>{error}</p>
        <button onClick={() => navigate("/")}>
          Back to Projects
        </button>
      </div>
    );
  }

  if (!project) {
    return <p>Project not found.</p>;
  }

  return (
    <div className="project-dashboard">
      <header className="page-header">
        <button
          onClick={() => navigate("/")}
          className="back-button"
        >
          ← Back to Projects
        </button>

        <h1>{project.name}</h1>
        <p>
          {project.description || "No description available."}
        </p>
      </header>

      <main>
        <section className="project-overview">
          <h2>Project Overview</h2>

          <div className="overview-grid">
            <div>
              <strong>Mode</strong>
              <span>{project.mode}</span>
            </div>

            <div>
              <strong>Category</strong>
              <span>{project.category}</span>
            </div>

            <div>
              <strong>Start Date</strong>
              <span>
                {project.start_date || "Not set"}
              </span>
            </div>

            <div>
              <strong>Target Completion</strong>
              <span>
                {project.target_completion_date}
              </span>
            </div>
          </div>
        </section>

        <section className="activities-section">
          <div className="section-header">
            <div>
              <h2>Activities</h2>
              <p>
                {project.activities?.length || 0} activities
              </p>
            </div>

            <button className="add-activity-button">
              + Add Activity
            </button>
          </div>

          {project.activities?.length > 0 ? (
            <div className="activities-table">
              <div className="activity-row activity-header">
                <span>Activity</span>
                <span>Duration</span>
                <span>Category</span>
                <span>Milestone</span>
              </div>

              {project.activities.map((activity) => (
                <div
                  className="activity-row"
                  key={activity.id}
                >
                  <span>{activity.name}</span>

                  <span>
                    {activity.duration} days
                  </span>

                  <span>
                    {activity.category || "—"}
                  </span>

                  <span>
                    {activity.is_milestone ? "Yes" : "No"}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <h3>No activities yet</h3>
              <p>
                Add activities to start building your
                event schedule.
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default ProjectDashboard;
