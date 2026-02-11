# CLAUDE.md — Maintenance Work Categorization System (MWCS)

This file is the single source of truth for any AI assistant (or developer) working
inside this repository.  Read it completely before touching code.

---

## 1. What This Project Is

A **Streamlit web application** that categorises maintenance work items loaded from
Excel files.  Each row ends up as **Accepted**, **Need Reconsideration**, or
**Rejected**, accompanied by an AI-generated justification and a confidence score.

Target audience: maintenance managers and operations analysts who need fast,
auditable decisions without writing code.

---

## 2. Deployment Context — Local Only

> **This application is designed for local development and local Streamlit
> execution via the terminal.  Do NOT build for cloud / production hosting.**

Typical run command:

```bash
streamlit run app.py
```

No Docker, no CI/CD pipeline, no cloud deployment artefacts are expected in this
repository at this time.

---

## 3. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| UI / Host | Streamlit >= 1.28.0 | Single-file or multi-page app |
| Language | Python 3.9+ | |
| Dataframes | Pandas >= 1.5.0, NumPy >= 1.24.0 | Core data manipulation |
| Excel I/O | openpyxl >= 3.10.0 | Read & write .xlsx |
| AI Justifications | Azure OpenAI (`openai >= 1.0.0`) | Primary; OpenRouter is fallback |
| Date Parsing | python-dateutil >= 2.8.0 | |
| Visualisation | Plotly >= 5.14.0 | Charts & flowchart previews |

All dependencies go in a single `requirements.txt`.

---

## 4. High-Level Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Streamlit UI Layer                    │
│  Screen 1: Upload → Screen 2: Rules → Screen 3: Preview│
│  Screen 4: Processing → Screen 5: Results & Export     │
└───────────────┬────────────────────┬───────────────────┘
                │                    │
        ┌───────▼──────┐   ┌────────▼────────┐
        │  Data Layer   │   │  Logic Engine   │
        │  (Pandas /    │   │  (Decision Tree │
        │   openpyxl)   │   │   Evaluator)    │
        └───────┬───────┘   └────────┬────────┘
                │                    │
        ┌───────▼────────────────────▼────────┐
        │       AI Justification Service       │
        │    (Azure OpenAI / OpenRouter API)   │
        └──────────────────────────────────────┘
```

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `app.py` | Streamlit entry-point; orchestrates screen flow |
| `upload.py` | File upload widget, schema detection, preview, validation |
| `rules.py` | Rule builder state, serialisation, template save/load |
| `logic_engine.py` | Parses rule definitions → decision tree; evaluates each row |
| `ai_service.py` | Calls the AI API; formats prompts; returns justification + confidence |
| `export.py` | Generates .xlsx / .csv / .json output files |
| `visualise.py` | Renders flowchart and sample-preview before processing |

> These module names are conventions, not mandates.  Refactor freely as long as
> the separation of concerns is maintained.

---

## 5. Data Flow (End-to-End)

1. User uploads one `.xlsx` workbook (main sheet + optional supporting sheets).
2. `upload.py` detects headers, validates required columns, previews 10 rows.
3. User defines hierarchical rules in the rule builder (`rules.py`).
4. `visualise.py` renders a colour-coded flowchart; user confirms or edits.
5. `logic_engine.py` iterates every row:
   - Evaluates rules top-to-bottom (AND / OR / NOT, nested if-then-else).
   - Performs lookups / joins / aggregations against supporting datasets.
   - Produces an intermediate decision + score.
6. `ai_service.py` receives the row data + decision context → returns a plain-
   English justification and a 0-100 confidence score.
7. Three columns are appended: **Status**, **Justification**, **ConfidenceScore**.
8. Results are displayed interactively; user can export via `export.py`.

---

## 6. Required & Optional Columns

### Main Dataset (mandatory upload)

| Required | Optional |
|---|---|
| Work ID | Asset ID |
| Description | Location |
| Priority | Cost Estimate |
| Category | Risk Level |
| Estimated Hours | Dependencies |
| Last Service Date | |

### Supporting Datasets (up to 5, all optional)

Common examples: Asset Registry, Budget Data, Availability Schedule,
Historical Data, Business Rules.  Each is a separate sheet in the same workbook
or a standalone `.xlsx`.

---

## 7. Rule Types the Logic Engine Must Support

| Type | Operators / Behaviour |
|---|---|
| Numeric | `>`, `<`, `=`, `>=`, `<=`, `between` |
| Text | `contains`, `exact match`, `regex` |
| Date | `before`, `after`, `within range` |
| Lookup | `match` (exists in ref dataset), `join` (retrieve value) |
| Aggregation | `Sum / Avg / Count` against threshold |
| Conditional | Nested `IF … THEN … ELSE` chains |
| Business Rule | Pre-defined compound rules (e.g. criticality-based) |

Operators combine with **AND**, **OR**, **NOT** at every nesting level.

---

## 8. Output & Confidence Bands

### Status Values
`ACCEPTED` | `RECONSIDER` | `REJECTED`

### Confidence Bands

| Band | Range | Implication |
|---|---|---|
| High | 85–100 % | Reliable; no manual check needed |
| Medium | 60–84 % | Minor review recommended |
| Low | 40–59 % | Borderline; manual review advised |
| Very Low | < 40 % | Flag for full manual review |

### Export Formats
`.xlsx` (preferred), `.csv` (UTF-8), `.json` (integration use).

### Audit Metadata (attach to every export)
Processing timestamp, logic version ID, record counts per category,
data-quality metrics, total processing duration.

---

## 9. AI Justification Guidelines

When prompting the AI model:

- Feed it the **row values**, the **rules that fired**, the **final decision**, and
  any **lookup results** that influenced the outcome.
- Ask for a 2-4 sentence plain-English explanation (target 500-1000 characters).
- Ask for a numeric confidence score (0-100).
- Include example outputs in the prompt so the model stays consistent:

  * **Accept example:** *"Maintenance work accepted. Priority is High, estimated
    hours (12) within quarterly budget (50 available), asset criticality Medium."*
  * **Reject example:** *"Maintenance work rejected. Estimated cost ($5,000)
    exceeds remaining departmental budget ($2,000)."*
  * **Reconsider example:** *"Requires review. Scheduled maintenance overdue
    (18 months), but resource availability limited to 8 hours this period."*

---

## 10. Performance & Resource Constraints

| Constraint | Target |
|---|---|
| Max rows tested | 100 k+ (design for 1 M+) |
| Processing throughput | ~10 000 rows / min |
| Min RAM | 4 GB |
| Max upload size | 500 MB |
| UI interaction latency | < 2 s |

Because the app runs locally, concurrency and multi-user concerns are out of
scope for now.

---

## 11. Security & Data Handling

- Treat all uploaded data as **sensitive**.
- Never persist data to disk beyond the active Streamlit session.
- No credential files should be committed; use environment variables or a local
  `.env` (git-ignored) for API keys.
- Add `.env` to `.gitignore` immediately.

---

## 12. Coding Conventions

1. **Python 3.9+** style.  Use type hints on all public function signatures.
2. Keep Streamlit-specific code in the UI layer; business logic must be testable
   without Streamlit.
3. Rule definitions are serialised as plain Python dicts (JSON-compatible) so
   templates can be saved/loaded trivially.
4. Write unit tests for `logic_engine.py` and `ai_service.py` at minimum.
5. Use `logging` (stdlib) — not `print` — for runtime diagnostics.
6. Favour explicit over implicit; avoid global mutable state.
7. Document every public function with a one-line docstring at the very least.

---

## 13. File / Directory Layout (Recommended)

```
portfolio_taai_scopeOptimization/
├── CLAUDE.md              ← this file
├── README.md
├── requirements.txt
├── .env.example           ← template for API keys (no secrets)
├── app.py                 ← Streamlit entry-point
├── src/
│   ├── __init__.py
│   ├── upload.py          ← file upload & validation
│   ├── rules.py           ← rule-builder state & templates
│   ├── logic_engine.py    ← decision-tree evaluator
│   ├── ai_service.py      ← AI API wrapper
│   ├── export.py          ← output generation
│   └── visualise.py       ← flowchart / preview rendering
├── templates/
│   └── (saved rule templates, .json)
├── tests/
│   ├── __init__.py
│   ├── test_logic_engine.py
│   └── test_ai_service.py
└── sample_data/
    └── sample_maintenance_data.xlsx   ← bundled example for onboarding
```

---

## 14. What Is Out of Scope (for now)

- Cloud / production deployment (Docker, CI/CD, managed hosting).
- Multi-user or concurrent-session support.
- Machine-learning–based rule suggestion.
- Real-time / streaming ingestion of new work items.
- Mobile interface.
- Role-based access control.
- ERP / CMMS system integration.

These are tracked as future enhancements in the PRD and should **not** influence
current implementation decisions.

---

## 15. Quick-Start Checklist (New Contributor)

1. Clone the repo and check out `claude/create-claude-md-mO5ri` (or the current
   feature branch).
2. Create a `.env` file (copy `.env.example`); add your Anthropic API key.
3. `pip install -r requirements.txt`
4. `streamlit run app.py`
5. Drop `sample_data/sample_maintenance_data.xlsx` into the upload widget.
6. Define or load a rule template, preview, and run a batch.
7. Verify export output.

---

*Document based on MWCS Product Requirements Document v1.0 — 2025-02-04*
