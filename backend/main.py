"""
FastAPI Backend for Maintenance Work Categorization System (MWCS)

This is the main entry point for the FastAPI backend that replaces the Streamlit UI.
All existing Python business logic is preserved and wrapped with REST API endpoints.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

# Import API routes
from api.routes import upload, rules, preview, process, export, datasets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting MWCS FastAPI Backend...")
    yield
    # Shutdown
    logger.info("Shutting down MWCS FastAPI Backend...")


# Create FastAPI app
app = FastAPI(
    title="Maintenance Work Categorization System API",
    description="REST API for the MWCS application - migrated from Streamlit to React + FastAPI",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative React dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MWCS API",
        "version": "2.0.0"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Maintenance Work Categorization System API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include API routers
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(rules.router, prefix="/api/rules", tags=["Rules"])
app.include_router(preview.router, prefix="/api/preview", tags=["Preview"])
app.include_router(process.router, prefix="/api/process", tags=["Process"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(datasets.router, prefix="/api/datasets", tags=["Datasets"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
