# Shutdown Maintenance Equipment Prioritization Platform

An end-to-end application that replaces spreadsheet-heavy shutdown planning workflows. The platform ingests canonical and supplementary equipment datasets, builds a single source of truth, and applies versioned AST-based rules to classify equipment as `Must Have`, `Good to Have`, or `Not Needed`.

## Implemented Scope

- Project dashboard with isolated workspaces
- Canonical and supplementary dataset uploads
- CSV and Excel ingestion with explicit modal-based sheet selection for Excel files
- Guided schema mapping grid with suggestions instead of raw JSON mapping
- Matching strategies for supplementary joins: exact, normalized, and fuzzy
- Column profiling and preview inspection before final upload
- Derived-column configuration with typed operators, operator-aware value inputs, and colored true/false/unknown outputs
- Dataset preview registry with permanent deletion
- Nested visual AST rule builder for `Must Have` and `Good to Have` logic
- Operator-aware rule and derived-condition editors with support for single-value, `BETWEEN`, and multi-value list inputs
- Equipment ID cleaning, compound expansion, transformed preview rows, and paged audit review before upload
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
docs/
  interactive-solution-guide.html
  onboarding-architecture-guide.md
```

## Start Here

If you are new to the project or reviewing it from a supervisor/stakeholder perspective, use this reading order:

1. This README for scope, setup, and major implemented features.
2. [Interactive Solution Guide](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/docs/interactive-solution-guide.html) for a product-oriented walkthrough.
3. [Onboarding And Architecture Guide](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/docs/onboarding-architecture-guide.md) for runtime flow, data model, API surface, code entry points, and current constraints.

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

## System Overview

The platform runtime currently works like this:

1. A project is created as the workspace boundary.
2. A canonical dataset is uploaded first.
3. Supplementary datasets are inspected, mapped, optionally cleaned, and uploaded afterward.
4. Each dataset can define derived columns and equipment ID cleaning rules.
5. During classification, every dataset is rebuilt through the same mapping, derived-column, and equipment-ID-cleaning pipeline.
6. Supplementary datasets are matched onto the canonical dataset and aggregated as evidence.
7. The latest ruleset AST is evaluated against the resulting master dataframe.
8. The run is stored with summary metadata and artifact-backed outputs.

For the detailed handover version of this flow, see [Onboarding And Architecture Guide](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/docs/onboarding-architecture-guide.md).

## Core Stored Entities

The main persisted entities are:

- `Project`: top-level workspace
- `Dataset`: uploaded canonical or supplementary file plus mapping, derived-column, matching, and cleaning config
- `RuleSet`: versioned AST rules for classification
- `ClassificationRun`: one execution of a ruleset against the rebuilt project dataframe
- `ClassificationRunArtifact`: stored row, explanation, and export files for a run

See [Onboarding And Architecture Guide](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/docs/onboarding-architecture-guide.md) for field-level interpretation and execution flow.

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

## Equipment ID Cleaning Methods

The intake flow can preprocess equipment IDs before matching. The cleaning pipeline is deterministic, audited, and applied consistently in preview, upload, and external test harness runs.

### 1. Whitespace Removal

Whitespace is removed before other cleaning logic and again after expansion.

- ` 101 A / 101B ` -> `101A`, `101B`

### 2. Bracket Removal With Optional Dash Bridging

Bracketed content is removed. When two alphanumeric fragments become adjacent, the cleaner can bridge them with `-`.

- `101A(CC)B` -> `101A-B`

### 3. Compound Split Expansion

Compound IDs are split on `&`, `/`, and `,`, then emitted as one final ID per row.

- `101A/101B` -> `101A`, `101B`
- `101A,101B` -> `101A`, `101B`

### 4. Simple Shorthand Inheritance

Short sibling tokens can inherit the missing prefix from the first token when the shorthand is unambiguous.

- `101A/B` -> `101A`, `101B`
- `101A,B` -> `101A`, `101B`

### 5. Last-Segment Replacement

If the first token has a stable shared prefix and the sibling token represents a replacement for the last hyphen segment, that shared prefix is preserved.

- `ET-0-LG-115AB/116AB` -> `ET-0-LG-115AB`, `ET-0-LG-116AB`
- `P-101A/102A` -> `P-101A`, `P-102A`

### 6. Inherit After The Last Hyphen

When a sibling token starts a new variant for the branch after the last `-`, the shared prefix before that final hyphen is inherited.

- `JB-DBP-TF1-1/1R2/08` -> `JB-DBP-TF1-1`, `JB-DBP-TF1-1R2`, `JB-DBP-TF1-08`

### 7. Alpha-Tail Replacement With Shared Numeric Suffix

When the first token ends in an alpha-only branch and another sibling reveals a shared numeric tail, that tail is propagated across the sibling expansions while preserving the shared prefix.

- `1-BNG-TH3-N/1R4/09-1` -> `1-BNG-TH3-N-1`, `1-BNG-TH3-1R4-1`, `1-BNG-TH3-09-1`

### 8. Alpha-Only Expansion Drop Rule

Any emitted expansion with no digits is dropped from the final output.

- `101A/ABC` -> `101A`

### Validation And Testing

The external harness in `external_tests/equipment_id_cleaning/` runs the same backend cleaning functions and now prints both the raw ID input and the final emitted IDs for each case.

## Main API Surface

The frontend talks to these main backend operations:

- inspect file before upload
- create and delete projects
- upload and delete datasets
- save latest ruleset version
- run classification
- page through prior run rows
- export classification CSV

The full endpoint summary is documented in [Onboarding And Architecture Guide](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/docs/onboarding-architecture-guide.md).

## Current Constraints

Important current boundaries:

- one canonical dataset per project
- latest ruleset is the primary working version in the UI
- equipment ID cleaning is deterministic rule-based preprocessing
- matching supports exact, normalized, and fuzzy strategies
- classification output is persisted as artifact-backed files rather than one large database row
