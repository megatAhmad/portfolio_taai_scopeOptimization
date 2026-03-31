# Shutdown Maintenance Equipment Prioritization Platform

An end-to-end Enterprise application designed to replace spreadsheet-heavy maintenance workflows. This platform consolidates diverse Equipment-to-Category reference datasets into a unified Source of Truth and evaluates them against a visually-programmed Abstract Syntax Tree (AST) logic engine to classify shutdown priorities.

## Core Features

- **Multi-Format Ingestion**: Upload massive reference datasets via CSV or Excel (`.xlsx`, `.xls`), with built-in UI interception allowing users to precisely declare their target Excel Sheets.
- **Type-Aware Derived Columns**: Map Supplementary datasources to your Canonical table utilizing deep typed evaluations (String, Float, Date). Support includes rich logic operators like `BETWEEN`, `>`, `<`, and multi-keyword substring handlers like `CONTAINS ANY` and `CONTAINS ALL`.
- **Visual Rule Builder**: Don't write code—dynamically generate nested `AND`/`OR` logic trees via a GUI. Rules are automatically checked for Data Types against the source schema and explicitly serialized to the Database with a fully version-controlled history.
- **Lifecycle Management**: Securely manage project isolation. Features granular Dataset Deletion and complete Cascading Project wipes that completely purge database linkages and physical disk files simultaneously.

## Tech Stack

**Frontend** 
- React (Vite)
- TypeScript
- TailwindCSS
- React Router DOM
- Lucide React

**Backend**
- Python 3.12+
- FastAPI (Uvicorn)
- Pandas & OpenPyXL (Execution Engine)
- SQLite (Persisted Storage)
- SQLAlchemy + Alembic (ORM & Migrations)

## Installation & Setup

Ensure you have Node.js and Python 3.12 installed on your system.

### 1. Backend Setup

Open a terminal and navigate to the `backend/` directory.

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Deploy the database schemas using Alembic:
```bash
alembic upgrade head
```

Boot the FastAPI application:
```bash
uvicorn app.main:app --reload --port 8000
```
*The API should now be running locally on http://127.0.0.1:8000.*

### 2. Frontend Setup

Open a new terminal session and navigate to the `frontend/` directory.

```bash
cd frontend
npm install
npm run dev
```

The application will provide a local web-server URL (typically http://localhost:5173). 

## Usage Guide
1. Create a **New Project** on the Dashboard.
2. In the Project detail view, click **Upload Dataset**. Add your *Canonical* dataset first. 
3. Proceed to upload your *Supplementary* datasets (CSV/Excel).
4. Supply your explicit mapping schema (i.e., mapping the source 'Equipment ID' to match the Canonical table). Use **Advanced Rules** to inject dynamic derivations if required.
5. Hit **Manage Rules** to open the Visual Rule Builder. Design your Must-Have vs. Good-to-Have criteria, press **Save Rule**, and finally fire **Run Classification** to view the evaluated matrices.
