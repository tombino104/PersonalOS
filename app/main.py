import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import __version__, config, db, seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.data_dir().mkdir(parents=True, exist_ok=True)
    conn = db.connect(config.db_path())
    try:
        db.migrate(conn)
        seed.sample_activities(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="Personal OS", version=__version__, lifespan=lifespan)


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
