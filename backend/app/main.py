from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Shutdown Maintenance Equipment Prioritization Platform API")

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:5173", # Default Vite port
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import projects, datasets, rules, runs

app.include_router(projects.router)
app.include_router(datasets.router)
app.include_router(rules.router)
app.include_router(runs.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
