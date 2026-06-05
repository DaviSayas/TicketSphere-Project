"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin, auth, categories, tickets, users
from app.core.config import settings
from app.db.session import Base, engine
from app.scheduler.runner import start_scheduler, stop_scheduler

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")


def _run_migrations():
    """Add columns that may not exist in pre-existing SQLite databases."""
    from sqlalchemy import inspect, text
    with engine.connect() as conn:
        cols = {c["name"] for c in inspect(engine).get_columns("tickets")}
        if "deleted_at" not in cols:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN deleted_at DATETIME"))
            conn.commit()
            logger.info("Migration: added tickets.deleted_at")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    start_scheduler()
    logger.info("Application started")
    yield
    # Shutdown
    stop_scheduler()
    logger.info("Application stopped")


app = FastAPI(
    title="Sistema de Gestão de Tickets",
    description="Helpdesk interno — FastAPI + SQLite + Vue 3",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(tickets.router)
app.include_router(admin.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


# ── Frontend SPA serving ──────────────────────────────────────────────────────
if FRONTEND_DIR.exists():
    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse(str(FRONTEND_DIR / "index.html"), headers={"Cache-Control": "no-cache"})

    for sub in ["src", "icons"]:
        sub_path = FRONTEND_DIR / sub
        if sub_path.exists():
            app.mount(f"/{sub}", StaticFiles(directory=str(sub_path)), name=f"static_{sub}")

    @app.get("/manifest.json", include_in_schema=False)
    async def manifest():
        mf = FRONTEND_DIR / "manifest.json"
        if mf.exists():
            return FileResponse(str(mf), media_type="application/json")

    @app.get("/service-worker.js", include_in_schema=False)
    async def sw():
        swf = FRONTEND_DIR / "service-worker.js"
        if swf.exists():
            return FileResponse(str(swf), media_type="application/javascript")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(request: Request, full_path: str):
        file_path = FRONTEND_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            ext_map = {".js": "application/javascript", ".css": "text/css",
                       ".json": "application/json", ".png": "image/png",
                       ".svg": "image/svg+xml", ".ico": "image/x-icon",
                       ".woff2": "font/woff2", ".woff": "font/woff"}
            ct = ext_map.get(file_path.suffix.lower(), "application/octet-stream")
            return FileResponse(str(file_path), media_type=ct)
        return FileResponse(str(FRONTEND_DIR / "index.html"), headers={"Cache-Control": "no-cache"})
else:
    @app.get("/", tags=["meta"])
    def root_api():
        return {"app": "TicketSphere", "version": "1.0.0", "status": "ok"}
