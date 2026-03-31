**PRODUCT REQUIREMENTS DOCUMENT**

# Shutdown Maintenance Equipment Prioritization Platform

A web application that consolidates multiple equipment-to-category datasets into a single auditable source of truth, then applies editable rules to classify shutdown equipment as Must Have, Good to Have, or Not Needed.

| Product | Shutdown Maintenance Equipment Prioritization Platform |
| --- | --- |
| Version | 1.0 (drafted from stakeholder brief) |
| Date | March 30, 2026 |
| Recommended stack | Backend: Python 3.13 + FastAPI • Frontend: React + TypeScript + Tailwind + component library |

| Primary outcome | Key differentiators |
| --- | --- |
| Enable planners to justify why each equipment item is in-scope for shutdown, with clear rule lineage and supporting source evidence. | Handles low-quality IDs, provides confidence-based semantic matching, exposes a visual rules tree, and keeps every decision auditable. |

## 1. Executive Summary

The product will help shutdown planners determine which equipment items are compulsory to maintain during a shutdown by combining multiple reference datasets into a single source of truth, then applying transparent, editable business rules to classify each equipment item as Must Have, Good to Have, or Not Needed.

The platform is designed for messy real-world data. Equipment identifiers may differ across datasets due to abbreviations, prefixes, suffixes, formatting noise, or alternate naming conventions. Therefore, the system must support deterministic matching first, confidence-based fuzzy and semantic matching second, and human review for low-confidence cases. Every derived classification must be explainable and auditable.

> **Core design principle**
>
> No black-box decisions. Every match and every final category must show its source datasets, rule path, confidence score, and any human override applied.

## 2. Problem Statement

Today, the user must manually VLOOKUP or reconcile several datasets that map equipment IDs to categories or tags. This creates five problems:

- The same equipment can appear differently across sources, causing failed lookups and hidden omissions.
- There is no single master view showing all categories tied to each equipment item.
- Decision logic is usually buried in spreadsheets, which makes it brittle, hard to reset, and difficult to audit.
- Stakeholders cannot easily verify why an equipment item was classified as compulsory or optional.
- Reporting is manual, so planners lose time producing counts, percentages, and justification packs for shutdown decisions.

The product must replace spreadsheet-heavy workflows with a guided web UI, a robust entity-matching layer, a versioned rules engine, and a downloadable results package.

## 3. Goals and Non-Goals

| Area | Definition |
| --- | --- |
| Goals | Create a guided workflow to upload one primary dataset and 6-7 supplementary datasets, map columns, resolve equipment identity, build a master dataset, define editable classification rules, review decisions, and export reports. |
| Decision outputs | Classify each original equipment row into Must Have, Good to Have, or Not Needed, with drill-down into source evidence and rule lineage. |
| Data quality goals | Handle low-quality IDs through normalization, aliases, fuzzy matching, semantic candidate generation, and human-in-the-loop review. |
| Governance goals | Version rules, version dataset snapshots, preserve audit logs, and store the exact rationale used for every classification run. |
| Non-goals (MVP) | Not a generic data catalog, not an ERP replacement, not a full MDM suite, and not a free-form natural-language decision engine without controlled rule semantics. |

## 4. Target Users and Jobs to Be Done

| User | Primary need | Success looks like |
| --- | --- | --- |
| Shutdown planner | Determine which equipment is mandatory during shutdown | Can upload data, run rules, inspect edge cases, and defend the final scope list quickly |
| Maintenance engineer | Validate technical rationale for inclusion/exclusion | Can open a row and see all source categories, confidence, and rule path |
| Data steward | Improve source mappings and clean poor identifiers | Can review low-confidence matches, add aliases, and reduce future ambiguity |
| Manager / approver | Review outcome at portfolio level | Can view dashboard counts, percentages, exceptions, and signed-off exports |

## 5. User Workflow

1. User uploads the original dataset and selects which column is the equipment ID.
1. User uploads each supplementary dataset and maps its Equipment ID column and Category column.
1. System profiles the data, standardizes identifiers, and attempts deterministic matches into a canonical equipment layer.
1. For unresolved rows, system proposes fuzzy and semantic match candidates with confidence scores and supporting rationale.
1. User reviews only ambiguous matches, approves or corrects them, and optionally adds aliases for future runs.
1. System builds the main df (single source of truth) by joining all category information back to the original dataset.
1. User creates or edits classification rules in a visual rule builder; the system shows both form view and tree view.
1. User runs classification and sees row-level results plus dashboard summaries by status, source coverage, and exceptions.
1. User exports the final report, including row-level data, summary metrics, rule version, and optional match audit package.

## 6. Functional Requirements

### 6.1 Data upload and schema mapping

- Support CSV and Excel uploads for the original dataset and at least 10 supplementary datasets in the same project.
- After upload, show a column preview and require the user to map: original equipment ID column; supplementary equipment ID column; supplementary category column.
- Allow users to rename datasets in the UI so business users can recognize source meaning (for example: Criticality, Regulatory, Spare availability, Historical scope).
- Persist a dataset profile that stores file metadata, column names, row counts, null rates, distinct count, and sample values.

### 6.2 Equipment identity resolution and matching

Matching must follow a layered strategy so precision stays high and review effort stays low.

| Stage | Method | Purpose | Audit fields captured |
| --- | --- | --- | --- |
| 1 | Normalization | Uppercase, trim, strip punctuation, normalize separators, collapse whitespace, standardize prefixes/suffixes | normalized_id, normalization_steps |
| 2 | Exact / deterministic | Match on canonical ID, known aliases, mapping tables, or exact normalized string | match_method, matched_value, alias_source |
| 3 | Fuzzy string | Use token-based and edit-distance similarity for near-matches and abbreviations | similarity_score, scorer_name, candidate_rank |
| 4 | Semantic candidate generation | Use embeddings or semantic similarity to surface likely matches where naming conventions differ materially | embedding_model, semantic_score, top_k_candidates |
| 5 | Human review | Require review below confidence threshold or when top candidates conflict | reviewer, decision, timestamp, rationale |

> **Matching acceptance policy**
>
> Only auto-accept matches above a configurable threshold and when there is clear separation from the second-best candidate. Everything else goes to a review queue. The threshold must be configurable per source dataset.

### 6.3 Main df / single source of truth builder

The system shall generate a canonical row set keyed by the original dataset. Each row in the original dataset remains present; supplementary category data is attached as additional columns or structured attributes.

| Requirement | Details |
| --- | --- |
| Minimum output fields | original_equipment_id, canonical_equipment_id, normalized_equipment_id, one category field per source dataset, final_classification, classification_reason, rule_path, confidence_summary, manual_override_flag |
| Lineage fields | matched_source_row_id, source_dataset_name, match_method, match_score, matched_on_value, alias_used, review_status |
| Conflict handling | When two supplementary rows map to one canonical row, preserve all candidates and apply source-specific precedence or aggregation rules. |
| Completeness | Rows without source matches must remain in the main df and be clearly labeled as unmatched or insufficient evidence. |

### 6.4 Rules engine and classification logic

- Users must be able to define rules with nested AND / OR / NOT groups.
- Rule operands must support: source category values, null/non-null checks, match confidence thresholds, manually approved flags, numeric thresholds, text contains, membership in lists, and custom Python functions.
- Rules must be versioned. A user can clone, edit, deactivate, reset, or roll back to prior rule versions.
- The system must show the rules in both builder form and tree form so users can visually verify logic before execution.
- Each classification result must store which exact rule node fired and the ordered explanation path.

> **Illustrative rule tree**

```
Classify = Must Have
IF (
  source_regulatory.category IN ['MANDATORY', 'COMPLIANCE']
  OR source_criticality.category IN ['CRITICAL', 'A1']
  OR custom_fn('is_shutdown_safety_item') == True
)
ELSE IF (
  source_historical_scope.category IN ['RECOMMENDED']
  OR match_confidence_summary >= 0.90
)
  => Good to Have
ELSE
  => Not Needed
```

### 6.5 Dashboard, validation, and exports

- Dashboard must show total counts and percentages for Must Have, Good to Have, and Not Needed.
- Provide filters by source dataset, classification, review status, confidence band, and rule version.
- Provide exception views: unmatched rows, low-confidence matches, conflicting source categories, and manual overrides.
- Allow users to inspect any row and see a side panel with source evidence, candidate matches, rule path, and audit trail.
- Exports must include at minimum: classified row-level dataset, summary dashboard metrics, match audit log, and rule definition snapshot.

### 6.6 Auditability and governance

- Every upload, mapping choice, match approval, alias creation, rule edit, rule execution, and export must generate an audit event.
- The system must preserve dataset version, rule version, model version (if semantic matching is used), and the user identity for changes.
- Users must be able to explain any final classification at row level without reading source code.

### 6.7 Extensibility / custom functions

The platform must be modular enough to accept new user-defined functions in future without rewriting the rules engine. Custom functions will be registered in the backend and exposed in the rule builder as approved operators.

> **Example plugin contract (illustrative)**

```python
class RulePlugin(Protocol):
    name: str
    description: str
    input_schema: dict
    return_type: Literal['bool', 'number', 'string']
    def evaluate(self, row: dict, context: dict) -> object: ...
```

## 7. UX and UI Requirements

The UI should feel like a polished analytical application, not a developer utility. It should combine a guided workflow with powerful inspection tools.

| Area | UX expectation | Suggested interaction pattern |
| --- | --- | --- |
| Project setup | Low-friction onboarding | Stepper or wizard with progress indicators and saved drafts |
| Schema mapping | Fast and understandable | Preview grid, column selectors, data profiling cards, and inline validation |
| Match review | Efficient triage of ambiguities | Queue view with side-by-side candidate comparison and approve / reject actions |
| Rule authoring | Business-readable logic | Form builder plus synchronized tree diagram and human-readable sentence preview |
| Results | Immediate clarity | Dashboard summary cards, drill-down table, filters, and row details drawer |

> **UI design recommendation**
>
> Use a modern React interface with strong typography, responsive cards, a high-density review table, and interactive diagrams. Avoid Streamlit for the main product UI unless a temporary internal prototype is needed.

## 8. Recommended Technical Architecture

The stack below balances developer speed, auditability, and a high-quality custom UI while staying aligned to the Python backend requirement.

| Layer | Recommendation |
| --- | --- |
| Frontend | React + TypeScript + Vite, Tailwind CSS, shadcn/ui for polished components, TanStack Table for data review, React Flow for rule-tree visualization, Apache ECharts for interactive charts. |
| Backend API | Python 3.13, FastAPI, Pydantic models, SQLAlchemy 2, Alembic migrations. |
| Data processing | Pandas or Polars for transforms; background job runner for heavier matching/classification runs; vector similarity layer for semantic candidate generation. |
| Storage | PostgreSQL for transactional data and audit logs; object storage or file store for uploaded datasets and exported reports. |
| Matching utilities | RapidFuzz for high-speed fuzzy string scoring; sentence-transformers or equivalent embedding models for semantic candidate retrieval. |
| Deployment | Containerized services behind a reverse proxy; separate worker process for long-running jobs; environment-based configuration and secrets management. |

## 9. Data Model (conceptual)

| Entity | Purpose | Key fields | Notes |
| --- | --- | --- | --- |
| project | Top-level workspace | project_id, name, created_by | Groups uploads, rules, runs, and exports |
| dataset_upload | Stores each uploaded file | dataset_id, project_id, file_path, schema_json, uploaded_at | Keeps source file metadata and versioning |
| column_mapping | Stores user column selections | dataset_id, equipment_id_col, category_col | Original dataset only needs equipment_id_col |
| canonical_equipment | Canonical equipment registry per project | canonical_id, canonical_label, alias_count | Can be seeded from original dataset first |
| match_record | Lineage for each source match | source_row_id, canonical_id, method, score, reviewer | Stores all accepted or candidate mappings |
| rule_set / rule_version | Versioned logic | rule_set_id, version_no, ast_json, status | Supports rollback and approval |
| classification_run | Execution snapshot | run_id, rule_version, dataset_versions, started_at | Stores aggregate stats and row outputs |
| audit_event | Change trace | event_type, actor, target_id, payload_json, timestamp | Supports governance and troubleshooting |

## 10. Non-Functional Requirements

| Attribute | Requirement |
| --- | --- |
| Explainability | A business user must be able to understand why a row was classified without opening backend code. |
| Performance target | Initial target: up to 100k original rows and 10 supplementary datasets should complete exact/fuzzy consolidation in a few minutes on a standard worker. Semantic review queues may be asynchronous. |
| Reliability | Classification runs must be reproducible from the same dataset versions and rule version. |
| Security | Role-based access for edit vs review vs export permissions; encrypted secrets; secure file handling. |
| Observability | Structured logs, job status tracking, error capture, and per-run metrics. |
| Accessibility | Keyboard-operable rule builder and review screens; sufficient contrast and readable density. |

## 11. Success Metrics and Acceptance Criteria

| Metric / criterion | Target | How it is validated |
| --- | --- | --- |
| Mapping productivity | User can configure one project end-to-end without spreadsheet VLOOKUP work | Observed in UAT using real business files |
| Match quality | High-confidence automatic matches are accurate and low-confidence cases are routed to review | Sample audit against manually verified benchmark rows |
| Decision transparency | 100% of final classifications show rule path and source evidence | Row inspection panel and export validation |
| Rule agility | User can edit, reset, or clone rules without code change | UAT scenario with rule versioning |
| Reporting | User can export row-level output plus summary counts and percentages | Download package review |

## 12. Risks and Mitigations

| Risk | Why it matters | Mitigation | Owner area |
| --- | --- | --- | --- |
| Poor source ID quality | Wrong joins can distort downstream classification | Multi-stage matching, thresholding, review queue, alias learning | Data / backend |
| Conflicting categories across sources | A row may receive contradictory signals | Source precedence, conflict flags, explicit rule precedence | Product / data |
| Rule sprawl | Too many ad hoc rules can become unmanageable | Versioning, folders/tags, naming conventions, approval flow | Product / governance |
| Opaque ML matching | Users may distrust semantic matching | Use semantic search only to generate candidates; keep human approval for ambiguity | Backend / UX |
| Large-file performance | User experience degrades with heavy datasets | Async jobs, chunked processing, progress indicators, optimized data engine | Engineering |

## 13. Proposed Delivery Phases

| Phase | Scope | Outcome |
| --- | --- | --- |
| Phase 1 - MVP | Upload workflow, schema mapping, deterministic + fuzzy matching, main df builder, rules engine, dashboard, export | Business users can replace the current spreadsheet workflow |
| Phase 2 | Semantic candidate generation, review queue, alias library, richer conflict resolution, approval workflow | Higher automation and better handling of messy identifiers |
| Phase 3 | Advanced governance, SSO/roles, reusable rule templates, project comparisons, API integrations | Enterprise readiness and operational scale |

## 14. Open Questions

- What is the expected row volume for the original dataset and each supplementary dataset?
- Are the three final classes fixed forever, or should administrators be able to add more outcome classes later?
- Do any source datasets have priority over others when categories conflict?
- Is there already a canonical equipment dictionary or alias list in the business today?
- Do exports need to follow a prescribed shutdown-report template or approval pack format?
- Will multiple users collaborate on the same project at once, requiring comments or approvals?

## Appendix A. Example row-level explanation output

> **Illustrative explanation**
>
> Equipment ID: P-101A
> Final classification: Must Have
> Rule fired: R1.2 > OR branch 2
> Why it fired:
> - source_criticality.category = 'A1'
> - match accepted from supplementary dataset 'Criticality Master'
> - match_method = fuzzy_token_set_ratio
> - match_score = 96.4
> - reviewer override = none

## Appendix B. Suggested project screen map

> **Recommended screen sequence**
>
> 1) Projects list / create project 2) Upload datasets 3) Column mapping and data profile 4) Match review queue 5) Main df explorer 6) Rule builder + tree preview 7) Classification results dashboard 8) Exports and audit history

End of document.
