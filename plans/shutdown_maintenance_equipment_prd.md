**PRODUCT REQUIREMENTS DOCUMENT**

# Shutdown Maintenance Equipment Prioritization Platform

A web application that consolidates multiple equipment-to-category datasets into a single auditable source of truth, then applies editable rules to classify shutdown equipment as Must Have, Good to Have, or Not Needed.

| Product | Shutdown Maintenance Equipment Prioritization Platform |
| --- | --- |
| Version | 2.0 (Updated post-implementation) |
| Recommended stack | Backend: Python 3.13 + FastAPI • Frontend: React + TypeScript + Tailwind + component library |

| Primary outcome | Key differentiators |
| --- | --- |
| Enable planners to justify why each equipment item is in-scope for shutdown, with clear rule lineage and supporting source evidence. | Handles low-quality IDs, provides confidence-based semantic matching, exposes a visual rules tree, directly accepts Excel/CSV files, and keeps every decision auditable. |

## 1. Executive Summary

The product helps shutdown planners determine which equipment items are compulsory to maintain during a shutdown by combining multiple reference datasets into a single source of truth, then applying transparent, editable business rules to classify each equipment item.

The platform is designed for messy real-world data. It officially supports both **CSV** and **Excel (.xlsx, .xls)** files and allows users to strictly declare targeted sheets. It features a completely dynamic rules engine that supports Date, Numeric, and Text comparisons (including `CONTAINS ANY`, `CONTAINS ALL`, and `BETWEEN` operations). Furthermore, full cascade-deletions for both overall Projects and isolated Datasets allow for deep workspace lifecycle management.

## 2. Problem Statement

Today, the user must manually VLOOKUP or reconcile several datasets that map equipment IDs to categories or tags. This creates five problems:

- The same equipment can appear differently across sources, causing failed lookups and hidden omissions.
- Decision logic is usually buried in spreadsheets, which makes it brittle, hard to reset, and difficult to audit.
- Stakeholders cannot easily verify why an equipment item was classified as compulsory or optional.
- There is no single master view showing all categories tied to each equipment item.

The product replaces spreadsheet-heavy workflows with a guided web UI, an entity-matching layer, a versioned rules engine, and downloadable results.

## 3. Goals

| Area | Definition |
| --- | --- |
| Goals | Create a guided workflow to upload primary and supplementary datasets (CSV + Excel), map columns, define editable classification rules, and run decision engine matrices. |
| Decision outputs | Classify each original equipment row into Must Have, Good to Have, or Not Needed. |
| Rule flexibility | Enable Data Typed evaluation metrics (String, Numeric, Date) granting rich logical operators like BETWEEN or multi-keyword CONTAINS. |
| Governance goals | Version rules dynamically via AST JSONs, store exact rationale, and allow permanent cascade deletions of incorrect projects/datasets. |

## 4. Target Users

| User | Primary need | Success looks like |
| --- | --- | --- |
| Shutdown planner | Determine which equipment is mandatory during shutdown | Can upload data, run rules, inspect edge cases, and defend the final scope list quickly |
| Maintenance engineer | Validate technical rationale for inclusion/exclusion | Can open a row and see all source categories, confidence, and rule path |

## 5. User Workflow

1. User creates a highly-isolated **Project**.
2. User uploads the Original Dataset (CSV or Excel) and selects what constitutes the Canonical Equipment ID. If an Excel file is chosen, the UI intercepts to explicitly request the target Sheet Name.
3. User uploads Supplementary Datasets, mapping Equipment IDs and generating **Derived Column Names** powered by advanced type-based conditions (e.g. `If Date BETWEEN 2024-01-01 and 2024-12-31 => "Due"`).
4. System builds the main dataframe mapping everything sequentially.
5. User navigates to the visual **Rule Builder** to draft Abstract Syntax Tree (AST) rules defining what makes an Equipment "Must Have" or "Good to Have".
6. User clicks 'Save Rule' (persisted instantly to the Database) and triggers 'Run Classification'.
7. User can freely delete misconfigured Datasets or entire Projects to flush files from the disk.

## 6. Functional Requirements

### 6.1 Data upload and schema mapping
- Support **CSV** and **Excel (.xlsx, .xls)**.
- For Excel uploads, a React Modal must intercept the raw file drop and prompt the user exactly which **Sheet Name** to extract.
- Preview a schema grid that allows user to generate mappings between the Supplementary Data and Canonical Data.
- Ability to permanently Delete a dataset (removes `.csv`/`.xlsx` off the disk and drops DB relations).
- Ability to permanently Delete an entire project (Cascading flush of all files, datasets, and rules).

### 6.2 Main df / Single source of truth builder
- Evaluates the Canonical rows and performs left joins using Pandas `read_csv` and `read_excel`.
- Columns are dynamically renamed based on user's definitions in the UI so that naming conflicts are avoided in the Rule Builder variables.

### 6.3 Rules Engine and Classification Logic
- **Derived Column Mapping**: Supports typed logic parsing. If 'Text', logic operators include `=`, `!=`, `CONTAINS`, `CONTAINS ANY`, `CONTAINS ALL`, `IN`. If 'Numeric' or 'Date', logic supports `<`, `>`, `<=`, `>=`, and `BETWEEN`.
- **Fallbacks**: Users can configure exactly what label is emitted if a rule is Not Fulfilled, or if the source cell is Null/Empty.
- **AST Generation**: Rule logic translates into Abstract Syntax Trees that are dynamically generated and viewable in the UI.
- **Database Saving**: The Rule Builder persists its AST via `createRuleSet` and automatically attempts to load the highest `version_no` upon access.

## 7. Recommended Technical Architecture

- **Frontend**: React + TypeScript + Vite, Tailwind CSS, Lucide React (Icons), and React Router for Page Navigation.
- **Backend**: Python 3.12+, FastAPI framework, Uvicorn Server.
- **Data Engine**: Pandas and OpenPyXL for memory-efficient dataframe transformations and Excel ingestion.
- **Database**: SQLite optimized with SQLAlchemy 2 ORM. Alembic for automated database migrations.

End of document.
