"""FastAPI 应用工厂"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path


def create_app(static_dir: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="熠觉 · Phosphene Web UI",
        version="2.1.0",
        description="AI 内容自动化工厂管理后台",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from web.routes import router as api_router
    app.include_router(api_router)

    if static_dir and static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
