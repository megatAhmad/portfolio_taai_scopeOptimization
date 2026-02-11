# MWCS FastAPI Backend

This is the FastAPI backend for the Maintenance Work Categorization System (MWCS), migrated from Streamlit to a modern React + FastAPI architecture.

## Features

- **RESTful API** for all MWCS operations
- **WebSocket support** for real-time processing progress
- **Session management** for multi-user support
- **File upload** with validation
- **Rule management** (standard, condition, function, AI-based)
- **Data processing** with AI justification generation
- **Export** in multiple formats (XLSX, CSV, JSON)
- **Supporting datasets** for lookups and enrichment

## Project Structure

```
backend/
├── main.py                    # FastAPI entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── api/
│   ├── routes/               # API route handlers
│   │   ├── upload.py         # File upload endpoints
│   │   ├── rules.py          # Rule management endpoints
│   │   ├── preview.py        # Preview endpoints
│   │   ├── process.py        # Processing endpoints + WebSocket
│   │   ├── export.py         # Export endpoints
│   │   └── datasets.py       # Supporting datasets endpoints
│   ├── models/               # Pydantic models
│   │   ├── upload.py
│   │   ├── rules.py
│   │   ├── process.py
│   │   └── export.py
│   └── services/             # Business logic services
│       ├── session_store.py  # In-memory session management
│       └── websocket.py      # WebSocket connection manager
└── src/                      # Existing business logic (copied from root)
    ├── upload.py
    ├── rules.py
    ├── logic_engine.py
    ├── enhanced_rule_engine.py
    ├── ai_service.py
    ├── export.py
    └── ...
```

## Setup

### Prerequisites

- Python 3.9 or higher
- pip

### Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Running the Server

Development mode with auto-reload:
```bash
uvicorn main:app --reload --port 8000
```

Production mode:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## API Endpoints

### Upload
- `POST /api/upload` - Upload Excel file
- `GET /api/upload/{session_id}/preview` - Get data preview
- `GET /api/upload/{session_id}/stats` - Get column statistics
- `GET /api/upload/{session_id}/sheets` - List available sheets

### Rules
- `GET /api/rules/{session_id}` - Get all rules
- `POST /api/rules/{session_id}/standard` - Create standard rule
- `POST /api/rules/{session_id}/condition` - Create condition rule
- `POST /api/rules/{session_id}/function` - Create function rule
- `POST /api/rules/{session_id}/ai` - Create AI rule
- `DELETE /api/rules/{session_id}/{rule_id}` - Delete rule
- `PUT /api/rules/{session_id}/{rule_id}` - Update rule
- `GET /api/rules/templates` - List templates
- `POST /api/rules/{session_id}/load-template` - Load template
- `POST /api/rules/{session_id}/save-template` - Save template
- `GET /api/rules/functions` - List predefined functions
- `POST /api/rules/{session_id}/connections` - Create rule connection
- `DELETE /api/rules/{session_id}/connections/{conn_id}` - Delete connection

### Preview
- `GET /api/preview/{session_id}/flowchart` - Get rule flowchart
- `GET /api/preview/{session_id}/sample` - Get sample evaluation

### Process
- `POST /api/process/{session_id}` - Start processing
- `WS /api/process/ws/{session_id}` - WebSocket for progress
- `GET /api/process/{session_id}/status` - Get processing status
- `GET /api/process/{session_id}/summary` - Get processing summary

### Export
- `GET /api/export/{session_id}/xlsx` - Export as Excel
- `GET /api/export/{session_id}/csv` - Export as CSV
- `GET /api/export/{session_id}/json` - Export as JSON
- `GET /api/export/{session_id}/metadata` - Get audit metadata
- `POST /api/export/{session_id}/filter` - Get filtered results

### Datasets
- `GET /api/datasets/equipment-classification` - Get equipment classifications
- `GET /api/datasets/work-type` - Get work type categories
- `GET /api/datasets/redundancy` - Get redundancy data
- `GET /api/datasets/decision-matrix` - Get decision matrix

## Development Status

### Completed
- ✅ FastAPI application structure
- ✅ Session management service
- ✅ WebSocket manager service
- ✅ Pydantic models for all endpoints
- ✅ Upload API routes (fully implemented)
- ✅ Rules API routes (stub implementation)
- ✅ Preview API routes (stub implementation)
- ✅ Process API routes (stub implementation)
- ✅ Export API routes (stub implementation)
- ✅ Datasets API routes (stub implementation)

### TODO
- ⏳ Complete rule creation/management logic
- ⏳ Implement flowchart generation
- ⏳ Implement sample evaluation preview
- ⏳ Implement full processing pipeline with WebSocket updates
- ⏳ Implement export functionality
- ⏳ Load supporting datasets
- ⏳ Add comprehensive error handling
- ⏳ Add request validation
- ⏳ Add authentication/authorization (if needed)
- ⏳ Add rate limiting
- ⏳ Add logging and monitoring
- ⏳ Write unit tests
- ⏳ Write integration tests

## Testing

Run tests (once implemented):
```bash
pytest
```

## CORS Configuration

The backend is configured to accept requests from:
- http://localhost:5173 (Vite dev server)
- http://localhost:3000 (Alternative React dev server)

Update `main.py` to add additional origins if needed.

## Session Management

Sessions are stored in-memory and automatically cleaned up after 24 hours of inactivity. For production deployment, consider using Redis or a database for session persistence.

## Environment Variables

See `.env.example` for all available configuration options:
- Azure OpenAI credentials
- OpenRouter credentials
- Application settings (log level, file size limits, etc.)

## License

[Your License Here]
