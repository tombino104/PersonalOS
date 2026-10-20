import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import __version__, auth, config, db, seed
from .api import errors
from .api.auth_routes import public_router
from .api.v1 import router as api_v1


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.data_dir().mkdir(parents=True, exist_ok=True)
    conn = db.connect(config.db_path())
    try:
        db.migrate(conn)
        seed.sample_activities(conn)
        auth.purge_expired_sessions(conn, datetime.now(timezone.utc))
    finally:
        conn.close()
    yield


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
