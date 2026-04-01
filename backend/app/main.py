from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db_migrations import migrate_database

migrate_database()

app = FastAPI(title='Shutdown Maintenance Equipment Prioritization Platform')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(router, prefix='/api')
