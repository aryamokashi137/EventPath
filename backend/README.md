# EventPath Scheduling Engine — Backend API

An advanced operational research and event project management backend built with **FastAPI**, **SQLAlchemy 2.0**, and **Python**. EventPath systematically addresses core limitations of traditional CPM/PERT scheduling engines by integrating dynamic DAG generation, schedule crashing optimization, Monte Carlo PERT simulations, domain-specific event templates, and vendor availability constraint verification.

---

## 🚀 Key Features & Research Gaps Addressed

1. **Dynamic AoN DAG Network & Extended Floats (Gap 1)**
   - Computes Critical Path Method (CPM) passes on Activity-on-Node directed acyclic graphs.
   - Calculates **Total Float** ($TF$), **Free Float** ($FF$), and **Interfering Float** ($IF$) to identify subtle event bottlenecks.
2. **Interactive "What-If" Schedule Crashing Engine (Gap 2)**
   - Cost-time trade-off optimization engine.
   - Iteratively crashes critical path activities with the lowest cost per day ($K_i$) under budget or target duration constraints.
3. **Probabilistic PERT Monte Carlo Simulation (Gap 3)**
   - Resolves **merge-event path bias** using 1,000+ stochastic triangular sampling runs.
   - Computes completion probability, percentiles ($P_{10}$ to $P_{95}$), activity **Criticality Indices**, and 50-point cumulative probability **S-Curves**.
4. **Event Planning Domain Templates (Gap 4)**
   - Pre-configured workflows for weddings (`WEDDING_STANDARD`) and corporate tech conferences (`TECH_CONFERENCE`).
   - Supports vendor categories (`VENUE`, `CATERING`, `AUDIO_VISUAL`), milestone tracking, and PERT 3-point estimates.
5. **Vendor Availability Constraint Verification (Gap 5)**
   - Maps relative activity schedules to calendar dates.
   - Identifies vendor availability window violations and multi-tasking overbooking conflicts with float consumption resolution advice.

---

## 🛠️ Technology Stack

- **Framework**: FastAPI (Python 3.14+)
- **ORM & Database**: SQLAlchemy 2.0 with SQLite / PostgreSQL support
- **Schema Validation**: Pydantic v2
- **Testing**: Pytest & TestClient (15/15 passing integration tests)
- **Server**: Uvicorn ASGI

---

## 💻 Quick Start & Setup

### 1. Prerequisites
- Python 3.10+ installed
- Virtual environment (`venv`)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/aryamokashi137/EventPath.git
cd EventPath/backend

# Create & activate virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Server
```bash
python -m uvicorn app.main:app --reload --port 8000
```
Access the interactive Swagger UI documentation at: **`http://127.0.0.1:8000/docs`**

### 4. Running Tests
```bash
.\venv\Scripts\python -m pytest
```

---

## 📡 Core API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/projects` | `POST` | Create a new project (CPM / PERT mode) |
| `/api/v1/projects` | `GET` | List all projects |
| `/api/v1/projects/{id}` | `GET` | Get project details & activities |
| `/api/v1/projects/{id}/activities` | `POST` | Add activity with PERT & Crashing parameters |
| `/api/v1/projects/{id}/network` | `GET` | Calculate CPM DAG with Total, Free & Interfering Float |
| `/api/v1/projects/{id}/crash` | `POST` | Execute Schedule Crashing & Duration Compression |
| `/api/v1/projects/{id}/monte-carlo` | `POST` | Run Monte Carlo Simulation & generate S-Curve data |
| `/api/v1/projects/template/{name}` | `POST` | Instantiate project from domain template |
| `/api/v1/projects/{id}/availability` | `GET` | Verify Vendor Availability & Overbooking conflicts |
