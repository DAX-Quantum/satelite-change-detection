import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes.stats import router as stats_router
from app.routes.spatial import router as spatial_router
from app.routes.changes import router as changes_router
from app.routes.warehouse import router as warehouse_router
from app.routes.sql_console import router as sql_router
from app.routes.analytics import router as analytics_router

app = FastAPI(
    title="Satellite Change Detection & DBMS Analytics API",
    description="Operational 3NF (PostGIS) & Data Warehouse (Star Schema) Analytics Service",
    version="1.0.0"
)

# CORS setup for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(analytics_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(spatial_router, prefix="/api")
app.include_router(changes_router, prefix="/api")
app.include_router(warehouse_router, prefix="/api")
app.include_router(sql_router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Satellite Change Detection DBMS",
        "database": "PostgreSQL 16 + PostGIS 3.4"
    }


# Frontend static assets mounted at root (after /api routes)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
