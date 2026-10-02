import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .config import settings
from .database import Base, engine
from .routes import analytics, entities, tickets

logger = logging.getLogger("supportops")
logging.basicConfig(level=logging.INFO)

STATIC_DIR = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Idempotente: garante que tabelas novas existam em bancos já inicializados.
    Base.metadata.create_all(bind=engine)
    logger.info("SupportOps API %s started", settings.app_version)
    yield


app = FastAPI(
    title=settings.app_name,
    description="ITSM & Analytics API for the SupportOps platform",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(tickets.router)
app.include_router(entities.router)
app.include_router(analytics.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/ui", include_in_schema=False)
def dashboard_ui() -> FileResponse:
    """Painel operacional (V5). Servido pela própria API, sem build step."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["system"])
def health_check() -> JSONResponse:
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        logger.exception("Database health check failed")
        db_ok = False

    payload = {
        "status": "ok" if db_ok else "degraded",
        "version": settings.app_version,
        "database": "up" if db_ok else "down",
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "dashboard": "/ui",
        "docs": "/docs",
        "health": "/health",
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )