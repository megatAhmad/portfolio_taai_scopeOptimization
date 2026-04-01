# Shutdown Maintenance Equipment Prioritization Platform

An end-to-end application that replaces spreadsheet-heavy shutdown planning workflows. The platform ingests canonical and supplementary equipment datasets, builds a single source of truth, and applies versioned AST-based rules to classify equipment as `Must Have`, `Good to Have`, or `Not Needed`.

## Implemented Scope

- Project dashboard with isolated workspaces
- Canonical and supplementary dataset uploads
- CSV and Excel ingestion with explicit modal-based sheet selection for Excel files
- Guided schema mapping grid with suggestions instead of raw JSON mapping
- Matching strategies for supplementary joins: exact, normalized, and fuzzy
- Column profiling and preview inspection before final upload
- Derived-column configuration with typed operators and fallback labels
- Dataset preview registry with permanent deletion
- Nested visual AST rule builder for `Must Have` and `Good to Have` logic
- Versioned ruleset persistence with stable node ids
- Classification run view with summary counts, evidence trace, and CSV export
- Cascade project deletion that removes linked datasets and stored files

## Tech Stack

### Frontend
- React + TypeScript + Vite
- Tailwind CSS
- React Router DOM
- Lucide React

### Backend
- Python 3.12+
- FastAPI
- Pandas + OpenPyXL
- SQLite + SQLAlchemy + Alembic

## Project Structure

```text
backend/
  app/
    api/
    core/
    services/
frontend/
  src/
    components/
    lib/
    pages/
    types/
```

## Local Setup

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The FastAPI server will start at `http://127.0.0.1:8000`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite app will start at `http://localhost:5173`.

## API Notes

- The SQLite database is managed through Alembic migrations in `backend/alembic/`
- Backend startup automatically upgrades `backend/data/app.db` to the latest schema
- Uploaded dataset files are stored under `backend/data/uploads/`
- Classification payloads are stored as artifact files under `backend/data/classification_runs/`
- The latest ruleset version is always loaded when the project workspace opens
- Classification runs are persisted and can be exported from the latest result view
- Earlier prototype databases are migrated forward automatically on first startup

## Migration Commands

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

## Suggested Workflow

1. Create a new project from the dashboard.
2. Upload the canonical dataset first.
3. For Excel files, choose the target sheet in the intercept modal.
4. Use the schema mapping grid to align source columns to canonical-friendly fields.
5. Upload supplementary datasets and choose their matching strategy.
6. Add derived columns where typed fallback logic is needed.
7. Build and save nested `Must Have` and `Good to Have` rule groups.
8. Run classification to generate the prioritized equipment matrix, inspect evidence, and export CSV.
