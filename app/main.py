"""
School Parking Management System - Main FastAPI Application
Hệ thống quản lý bãi đỗ xe trường học
"""

import os
import sys
import warnings

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module=r"google\.api_core\._python_version_support",
)

venv_python = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".venv",
    "Scripts",
    "python.exe",
)

# If launched with a different interpreter, restart with the project's venv.
if (
    os.path.exists(venv_python)
    and os.path.abspath(sys.executable) != os.path.abspath(venv_python)
    and os.environ.get("SPM_REEXEC") != "1"
):
    os.environ["SPM_REEXEC"] = "1"
    os.execv(venv_python, [venv_python, *sys.argv])

# Allow running this file directly: `python app/main.py`.
if __package__ is None or __package__ == "":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.base import Base
from app.db.runtime_migration import apply_runtime_migrations
from app.db.session import engine

# Ra lệnh tạo toàn bộ bảng (Users, Vehicles, Transactions) nếu chưa có
Base.metadata.create_all(bind=engine)
if engine.dialect.name == "mssql":
    apply_runtime_migrations(engine)
# Khởi tạo FastAPI app
app = FastAPI(
    title="School Parking Management API",
    description="Hệ thống quản lý bãi đỗ xe thông minh cho trường học",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên cấu hình cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "School Parking Management System API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn

    reload_enabled = os.getenv("UVICORN_RELOAD", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload_enabled,
        reload_dirs=[app_dir],
        log_level="info"
    )