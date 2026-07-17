"""FastAPI 应用工厂"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path
import os


class SPAStaticFiles(StaticFiles):
    """Serve the React entry point for client-side routes, never for unknown APIs."""

    async def get_response(self, path: str, scope):
        is_api_path = path.replace("\\", "/").startswith("api/")
        if is_api_path:
            raise StarletteHTTPException(status_code=404)
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or is_api_path:
                raise
            return await super().get_response("index.html", scope)
        if response.status_code == 404 and not is_api_path:
            return await super().get_response("index.html", scope)
        return response


def create_app(static_dir: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="熠觉 · Phosphene Web UI",
        version="2.2.0",
        description="AI 内容自动化工厂管理后台",
    )

    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "PHOSPHENE_ALLOWED_ORIGINS",
            "http://127.0.0.1:5000,http://localhost:5000,http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    from web.routes import router as api_router
    app.include_router(api_router)

    if static_dir and static_dir.exists():
        app.mount("/", SPAStaticFiles(directory=str(static_dir), html=True), name="static")

    return app
