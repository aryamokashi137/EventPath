# EventPath: Critical Path Method (CPM) & PERT Scheduling Engine

EventPath is a production-quality, high-performance CPM (Critical Path Method) and PERT (Program Evaluation and Review Technique) computational scheduling engine tailored for event planning projects. It handles task dependencies, schedules events, identifies critical bottlenecks, evaluates completion probabilities, and simulates proposed changes in real-time.

---

## 1. How the CPM/PERT Engine Works (Operations Research Guide)

This section provides a clear mathematical explanation of the computational engine located in `app/services/cpm_engine.py`. This core engine is written in **pure Python** without any framework or database dependencies, making it independently testable and mathematically verifiable.

```
                  +---------------------------+
                  |  1. Parse Activities List |
                  +-------------+-------------+
                                |
                                v
                  +---------------------------+
                  |  2. Add START & END Nodes |
                  +-------------+-------------+
                                |
                                v
                  +---------------------------+
                  | 3. DFS & Cycle Detection  | ---> Loop Detected? -> Raise CycleDetectedError
                  +-------------+-------------+
                                | No Loop
                                v
                  +---------------------------+
                  | 4. Fulkerson Topological  |
                  |     Node Numbering        |
                  +-------------+-------------+
                                |
                                v
                  +---------------------------+
                  |   5. Forward Pass (ES/EF) |
                  +-------------+-------------+
                                |
                                v
                  +---------------------------+
                  |  6. Backward Pass (LS/LF) |
                  +-------------+-------------+
                                |
                                v
                  +---------------------------+
                  | 7. Slack & Critical Path  |
                  +---------------------------+
```

### 1.1 Graph Construction & Virtual Nodes
To calculate scheduling parameters reliably, the engine translates user-defined activities and dependencies into a **Directed Acyclic Graph (DAG)**. 
- **Nodes** represent activities (Activity-on-Node representation).
- **Edges** represent directed dependencies where an edge $A \to B$ indicates "activity $B$ cannot start until activity $A$ finishes."
- **Virtual Nodes**: To ensure a single entry and exit point for the network math:
  - A virtual **`START`** node (duration = $0.0$) is created and connected as a predecessor to all activities that have no user-defined predecessors.
  - A virtual **`END`** node (duration = $0.0$) is created and connected as a successor to all activities that have no successors.
  - If a project contains no activities, `START` is linked directly to `END`.

### 1.2 Cycle Detection & Fulkerson's Rule
- **Cycle Detection**: Event planning networks must not contain circular dependencies (e.g., $A \to B \to C \to A$). The engine runs a Depth-First Search (DFS) with a **three-color marking algorithm** (White: unvisited, Gray: visiting, Black: visited). If a Gray node is re-encountered, a cycle is detected, and the engine raises a custom `CycleDetectedError` listing the exact loop sequence (e.g., `Task A -> Task B -> Task C -> Task A`).
- **Fulkerson's Rule Numbering**: To compute the forward and backward passes, the nodes must be ordered such that every dependency edge goes from a lower-numbered node to a higher-numbered node. The engine implements a deterministic **topological sort** on the DAG. The indices in this sorted list act as the Fulkerson numbers.

### 1.3 CPM Forward Pass (Earliest Times)
Moving forward through the topological sort order, we calculate:
1. **Earliest Start (ES)**: The earliest possible time an activity can begin. It is the maximum of the Earliest Finishes of all its immediate predecessors:
   $$ES_i = \max_{j \in \text{predecessors}(i)} (EF_j)$$
   *(Note: $ES_{START} = 0.0$)*
2. **Earliest Finish (EF)**: The earliest possible completion time of an activity:
   $$EF_i = ES_i + d_i$$
   *(where $d_i$ is the duration of activity $i$)*

The total project duration is the Earliest Finish of the virtual `END` node ($EF_{END}$).

### 1.4 CPM Backward Pass (Latest Times)
Moving backward through the reverse topological order, we calculate:
1. **Latest Finish (LF)**: The latest time an activity can finish without delaying the project. It is the minimum of the Latest Starts of all its immediate successors:
   $$LF_i = \min_{k \in \text{successors}(i)} (LS_k)$$
   *(Note: $LF_{END} = EF_{END}$)*
2. **Latest Start (LS)**: The latest time an activity can begin without delaying the project:
   $$LS_i = LF_i - d_i$$

### 1.5 Slack & Critical Path Sequence
- **Slack (Total Float)**: The amount of time an activity can be delayed without delaying the project completion date. It is calculated as:
  $$Slack_i = LS_i - ES_i = LF_i - EF_i$$
- **Critical Activities**: Activities with $Slack \approx 0.0$ are critical. Any delay in these activities directly delays the project.
- **Critical Path Sequence**: The engine starts at the `START` node and traverses critical successors (where $Slack \approx 0.0$ and $ES_{successor} = EF_{current}$) to establish a continuous sequence of critical activity IDs leading to the `END` node.

---

### 1.6 PERT Analysis (Probabilistic Scheduling)
When a project is set to **PERT mode**, durations are treated as random variables. For each activity, the user provides three estimates:
- **Optimistic Time ($O$)**: Minimum possible duration.
- **Most Likely Time ($M$)**: Mode of the duration distribution.
- **Pessimistic Time ($P$)**: Maximum possible duration.

Using the **Beta distribution** approximations:
1. **Expected Time ($T_E$)**:
   $$T_E = \frac{O + 4M + P}{6}$$
2. **Activity Variance ($V$)**:
   $$V = \left(\frac{P - O}{6}\right)^2$$

The engine runs the standard CPM forward and backward passes using the expected times ($T_E$) as durations to determine the critical path.
- **Project Variance ($\sigma^2_P$)**: Sum of variances of activities **on the critical path**:
  $$\sigma^2_P = \sum_{i \in \text{critical path}} V_i$$
- **Project Standard Deviation ($\sigma_P$)**: $\sqrt{\sigma^2_P}$
- **On-Time Completion Probability**: Given a user-defined target completion date, we compute the target duration in days $T$. We calculate the standard normal Z-score:
  $$Z = \frac{T - \mu_P}{\sigma_P}$$
  *(where $\mu_P = EF_{END}$)*
  
  The probability of completion on or before the target date is computed using the Cumulative Distribution Function (CDF) of the standard normal distribution:
  $$P(\text{Completion} \le T) = \Phi(Z)$$

---

### 1.7 What-If Simulations
The what-if simulation allows planners to preview the impact of potential scheduling changes (e.g. changing an activity's duration or altering its predecessors) without saving them. The engine:
1. Computes the baseline network parameters.
2. Applies the proposed changes to the activities list in-memory.
3. Validates that the proposed change does not introduce cycles.
4. Computes the new CPM/PERT parameters.
5. Computes the **delta**:
   - Flipped to Critical: Activities that were non-critical but became critical.
   - Flipped to Non-Critical: Activities that were critical but became non-critical.
   - New project duration and probability.

---

## 2. Tech Stack

- **Python 3.11+**
- **FastAPI**: Web framework for high-performance REST APIs.
- **SQLAlchemy (2.0 style)**: Database ORM.
- **Alembic**: Database migrations management.
- **PostgreSQL**: Production-grade relational database.
- **Pydantic v2**: Response/Request data validation.
- **pytest & httpx**: Testing framework and API client testing.
- **SciPy**: Standard normal distribution CDF computations.

---

## 3. Local Setup & Installation

All commands below should be run from inside the `backend` directory. First, navigate to the folder:
```bash
cd backend
```

### 3.1 Create a Virtual Environment
In the `backend` directory of the project, run:
```powershell
python -m venv venv
```

Activate the virtual environment:
- **Windows (PowerShell)**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (CMD)**:
  ```cmd
  .\venv\Scripts\activate.bat
  ```
- **Linux/macOS**:
  ```bash
  source venv/bin/activate
  ```

### 3.2 Install Dependencies
Install all required libraries:
```bash
pip install -r requirements.txt
```

### 3.3 Configure the Environment
Create or edit the `.env` file in the `backend` folder:
```ini
# PostgreSQL connection string
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/eventpath

# Or to run using a local SQLite file for quick testing:
# DATABASE_URL=sqlite:///./eventpath.db
```

---

## 4. Running Migrations & Seeding

Ensure you are inside the `backend` directory and your virtual environment is activated:

### 4.1 Apply Migrations
Use Alembic to create tables in the database:
```bash
alembic upgrade head
```

### 4.2 Seed the Database
Populate the database with a pre-configured sample wedding project containing 10 activities and complex relationships:
```bash
python seed.py
```
*(If you are using SQLite, make sure your `.env` is set to SQLite, or pass the env variable inline in PowerShell)*:
```powershell
$env:DATABASE_URL="sqlite:///./eventpath.db"; python seed.py
```

---

## 5. Running the Application

Ensure you are inside the `backend` directory and your virtual environment is activated:
```bash
uvicorn app.main:app --reload
```

- **Interactive API Documentation (Swagger UI)**: Access at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc alternate documentation**: Access at [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 6. Running Tests

Ensure you are inside the `backend` directory and your virtual environment is activated:
- **Windows (PowerShell)**:
  ```powershell
  $env:PYTHONPATH="."; pytest -v
  ```
- **Linux/macOS**:
  ```bash
  PYTHONPATH=. pytest -v
  ```

---

## 7. API Endpoints

The API is fully versioned and available under `/api/v1`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/api/v1/projects` | Creates a new CPM or PERT project. |
| **GET** | `/api/v1/projects/{project_id}` | Fetches a project with all its activities and dependencies. |
| **PUT** | `/api/v1/projects/{project_id}` | Updates general project metadata. |
| **DELETE** | `/api/v1/projects/{project_id}` | Deletes a project and cascades deletion to activities. |
| **POST** | `/api/v1/projects/{project_id}/activities` | Adds a new activity to a project with predecessor references. |
| **PUT** | `/api/v1/projects/{project_id}/activities/{activity_id}` | Updates details or predecessors of an existing activity. |
| **DELETE** | `/api/v1/projects/{project_id}/activities/{activity_id}` | Deletes an activity and cleans up its dependency relations. |
| **GET** | `/api/v1/projects/{project_id}/network` | Computes the network forward/backward pass, returning slack, critical paths, and edges. |
| **GET** | `/api/v1/projects/{project_id}/pert` | Returns PERT statistics: expected duration, variance, and completion probability. |
| **POST** | `/api/v1/projects/{project_id}/simulate` | Performs a what-if simulation for a hypothetical change. |
