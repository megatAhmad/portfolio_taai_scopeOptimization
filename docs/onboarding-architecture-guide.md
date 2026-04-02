# Onboarding And Architecture Guide

This document is the practical handover view of the platform. It is intended for:

- new engineers who need to understand where the logic lives
- reviewers or supervisors who want to understand what the platform currently does
- maintainers who need a reliable map from UI actions to backend behavior

## What The Platform Does

The platform helps users turn messy shutdown-planning spreadsheets into an auditable prioritization workflow.

At a high level it:

1. creates isolated projects
2. ingests canonical and supplementary datasets
3. inspects files before upload
4. maps source columns into a normalized working shape
5. optionally applies equipment ID cleaning and expansion
6. optionally creates derived helper columns
7. joins supplementary evidence back to the canonical dataset
8. evaluates versioned AST rules
9. persists classification runs and export artifacts

## Runtime Flow

### 1. Project Workspace

The main UI flow starts in:

- [ProjectPage.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/pages/ProjectPage.tsx)

This page loads:

- project metadata
- uploaded datasets
- the latest ruleset
- the latest classification run summary and rows

Key backend endpoint:

- [routes.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/api/routes.py#L180)

### 2. Dataset Inspection Before Upload

The upload workflow lives in:

- [DatasetUploadForm.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/components/DatasetUploadForm.tsx)

The inspect step calls:

- [api.ts](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/lib/api.ts#L24)
- [routes.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/api/routes.py#L81)

The inspect endpoint can:

- read CSV or Excel files
- require explicit sheet selection for Excel
- profile columns
- generate schema mapping suggestions
- preview equipment ID cleaning output and audit rows
- preview derived-column audit output without final upload

### 3. Dataset Upload And Persistence

The final upload step calls:

- [api.ts](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/lib/api.ts#L29)
- [routes.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/api/routes.py#L211)

During upload, the backend:

1. saves the raw file
2. reads the selected sheet if needed
3. applies mapping rules
4. validates the chosen equipment ID column and join column
5. resolves and applies derived columns
6. applies equipment ID cleaning to the mapped equipment ID column
7. stores preview rows and schema profile for later inspection

### 4. Prepare Dataset For Matching

Every dataset used in classification is rebuilt through:

- [dataframe_engine.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/services/dataframe_engine.py#L383)

That function applies, in order:

1. file read
2. mapping
3. derived columns
4. equipment ID cleaning and expansion

This is important because preview behavior, upload behavior, and classification-time behavior are meant to stay aligned.

### 5. Master Dataframe Construction

Canonical and supplementary datasets are merged in:

- [dataframe_engine.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/services/dataframe_engine.py#L466)

Behavior:

- canonical dataset stays as the left-hand anchor
- supplementary datasets are matched one by one
- duplicate supplementary matches are preserved as aggregated evidence rather than overwritten
- per-dataset matching metadata is added, including method, count, confidence, source ids, and evidence rows

### 6. Rule Authoring And Versioning

The classification rule UI lives in:

- [RuleBuilder.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/components/RuleBuilder.tsx)

Current behavior:

- rules are edited through a visual flowchart plus inspector pattern
- the saved structure is still an AST, not a graph-native storage model
- condition editors are operator-aware
- supported input modes are single-value, `BETWEEN`, and multi-value list
- ruleset saves always create a new version

Ruleset API endpoints:

- create: [routes.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/api/routes.py#L310)
- latest: [routes.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/api/routes.py#L323)

### 7. Classification Run

Classification is triggered from:

- [ProjectPage.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/pages/ProjectPage.tsx#L89)

Backend entrypoint:

- [routes.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/api/routes.py#L328)

The classify flow:

1. load canonical dataset
2. load supplementary datasets
3. load latest ruleset
4. build the master dataframe
5. evaluate the AST rules
6. assign `Must Have`, `Good to Have`, or fallback label
7. persist rows and explanations as artifacts
8. return the first page of result rows and explanations

Core evaluation logic:

- [dataframe_engine.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/services/dataframe_engine.py#L535)

## Core Stored Entities

The main persistent models live in:

- [models.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/models.py)

### Project

A project is the top-level workspace.

It owns:

- datasets
- rulesets
- classification runs

### Dataset

A dataset stores both source metadata and the selected transformation settings.

Key persisted fields:

- source file path and file name
- role: canonical or supplementary
- selected sheet name
- equipment ID column
- canonical join column
- mapping rules
- derived columns
- schema profile
- preview rows
- matching configuration
- equipment ID cleaning configuration

### RuleSet

A ruleset stores:

- project link
- version number
- name
- full AST JSON

Only the latest version is used for new classification runs.

### ClassificationRun

A classification run stores:

- project link
- ruleset id and ruleset version
- summary counts
- visible columns
- total row count

The full rows and explanations are stored separately as artifacts.

### ClassificationRunArtifact

Artifacts store the heavier outputs for scale:

- result rows
- explanations
- export CSV

## API Surface Summary

Frontend API client:

- [api.ts](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/lib/api.ts)

Important endpoints:

- `GET /api/health`
  Purpose: basic backend health check
- `POST /api/datasets/inspect-file`
  Purpose: inspect uploads, preview schema, cleaning, and derived audits before upload
- `GET /api/projects`
  Purpose: list projects
- `POST /api/projects`
  Purpose: create project
- `GET /api/projects/{project_id}`
  Purpose: load project detail, datasets, latest ruleset, and latest run
- `DELETE /api/projects/{project_id}`
  Purpose: cascade delete project and linked files/artifacts
- `POST /api/projects/{project_id}/datasets`
  Purpose: upload dataset with mapping, derived columns, matching config, and cleaning config
- `DELETE /api/datasets/{dataset_id}`
  Purpose: delete one dataset
- `POST /api/projects/{project_id}/rulesets`
  Purpose: create a new versioned ruleset
- `GET /api/projects/{project_id}/rulesets/latest`
  Purpose: fetch latest ruleset
- `POST /api/projects/{project_id}/classify`
  Purpose: build master dataframe, evaluate rules, persist run artifacts
- `GET /api/projects/{project_id}/classification-runs`
  Purpose: list prior runs
- `GET /api/classification-runs/{run_id}`
  Purpose: get run summary
- `GET /api/classification-runs/{run_id}/rows`
  Purpose: page through run rows and explanations
- `GET /api/classification-runs/{run_id}/export`
  Purpose: download CSV export

## Equipment ID Cleaning Summary

Implementation:

- [equipment_id_cleaning.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/services/equipment_id_cleaning.py)

The platform currently supports:

- whitespace cleanup before and after expansion
- bracket removal with optional dash bridging
- compound splitting on `&`, `/`, and `,`
- shorthand inheritance such as `101A/B`
- last-segment replacement such as `ET-0-LG-115AB/116AB`
- inherit-after-last-hyphen such as `JB-DBP-TF1-1/1R2/08`
- alpha-tail replacement with shared numeric suffix such as `1-BNG-TH3-N/1R4/09-1`
- dropping alpha-only emitted tokens
- row expansion with audit records

External validation harness:

- [run_equipment_id_cleaning_checks.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/external_tests/equipment_id_cleaning/run_equipment_id_cleaning_checks.py)
- [equipment_id_cleaning_cases.json](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/external_tests/equipment_id_cleaning/equipment_id_cleaning_cases.json)

## Derived Columns Summary

Derived column UI:

- [DatasetUploadForm.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/components/DatasetUploadForm.tsx#L827)

Evaluation logic:

- [dataframe_engine.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/services/dataframe_engine.py#L253)

Current behavior:

- supports text, numeric, and date conditions
- supports `BETWEEN`
- supports list-style text operators such as `CONTAINS ANY`, `CONTAINS ALL`, and `IN`
- supports operator-aware editor states instead of one generic value field
- supports `true_value`, `false_value`, and `null_value`
- exposes derived audit rows in the inspection workflow

## Classification Rule Summary

Rule authoring UI:

- [RuleBuilder.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/components/RuleBuilder.tsx)

Current rule model:

- `must_have`
- `good_to_have`
- `fallback_label`

Each AST uses:

- group nodes with `AND` or `OR`
- condition nodes with typed operators
- stable node ids for explanation traces

Execution order:

1. evaluate `must_have`
2. if false, evaluate `good_to_have`
3. otherwise assign fallback label

## Where To Start Reading The Code

For frontend understanding:

- [Layout.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/components/Layout.tsx)
- [DashboardPage.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/pages/DashboardPage.tsx)
- [ProjectPage.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/pages/ProjectPage.tsx)
- [DatasetUploadForm.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/components/DatasetUploadForm.tsx)
- [RuleBuilder.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/components/RuleBuilder.tsx)
- [ResultsPanel.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/components/ResultsPanel.tsx)

For backend understanding:

- [routes.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/api/routes.py)
- [dataframe_engine.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/services/dataframe_engine.py)
- [equipment_id_cleaning.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/services/equipment_id_cleaning.py)
- [classification_storage.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/services/classification_storage.py)
- [models.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/models.py)
- [schemas.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/schemas.py)

## Current Constraints And Known Gaps

These are not necessarily bugs, but they are important for handover clarity.

- There is currently one canonical dataset per project.
- The UI and docs are strongest around the latest ruleset, not full historical ruleset comparison.
- Equipment ID cleaning is rule-based and deterministic, not ML-based or user-trainable.
- Matching uses exact, normalized, and fuzzy strategies, but does not yet expose richer conflict-resolution workflows in the UI.
- The rule builder is a visual flowchart editor backed by AST state, not a freeform graph storage model.
- Derived-column and equipment ID audits are preview tools; they help validation before upload, but they are not a full workflow engine.

## Recommended Reading Order For A New Joiner

1. Read [README.md](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/README.md)
2. Read [interactive-solution-guide.html](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/docs/interactive-solution-guide.html)
3. Read this architecture guide
4. Walk through [ProjectPage.tsx](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/frontend/src/pages/ProjectPage.tsx)
5. Walk through [routes.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/api/routes.py)
6. Trace [dataframe_engine.py](/home/percy/code/gptCodex/codexVersion/portfolio_taai_scopeOptimization/backend/app/services/dataframe_engine.py) from dataset preparation to classification
