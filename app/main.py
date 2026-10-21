import asyncio
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from . import __version__, auth, config, db, seed, setup
from .api import errors
from .api.auth_routes import public_router
from .api.v1 import router as api_v1
from .plugins import scheduler
from .plugins.registry import Registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.data_dir().mkdir(parents=True, exist_ok=True)
    conn = db.connect(config.db_path())
    try:
        db.migrate(conn)
        seed.sample_activities(conn)
        auth.purge_expired_sessions(conn, datetime.now(timezone.utc))
        setup.ensure_code(conn)
    finally:
        conn.close()
    registry = Registry()
    registry.load(config.plugins_dir(), datetime.now(timezone.utc))
    registry.apply_defaults(datetime.now(timezone.utc))
    app.state.plugins = registry
    scheduler_task = asyncio.create_task(scheduler.run(registry))
    try:
        yield
    finally:
        scheduler_task.cancel()
        registry.shutdown()


_docs_enabled = os.environ.get("ENABLE_DOCS") == "1"

app = FastAPI(
    title="Personal OS",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)
errors.install(app)
app.include_router(public_router)
app.include_router(api_v1)


@app.get("/health")
def health() -> JSONResponse:
    try:
        conn = db.connect(config.db_path())
        try:
            conn.execute("SELECT 1 FROM schema_migrations LIMIT 1")
        finally:
            conn.close()
        ok = True
    except (OSError, sqlite3.Error):
        ok = False
    return JSONResponse(
        {"status": "ok" if ok else "error", "version": __version__, "database": ok},
        status_code=200 if ok else 503,
    )


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
    "form-action 'self'"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if not request.url.path.startswith(("/docs", "/openapi.json")):
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    return response


def web_dir() -> Path:
    configured = os.environ.get("WEB_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent / "web" / "dist"


@app.get("/{path:path}", include_in_schema=False)
def web(path: str) -> FileResponse:
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404, detail="not found")
    root = web_dir().resolve()
    index = root / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="web interface not built")
    if path:
        candidate = (root / path).resolve()
        if candidate.is_file() and candidate.is_relative_to(root):
            headers = {}
            if path.startswith("assets/"):
                headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return FileResponse(candidate, headers=headers)
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
