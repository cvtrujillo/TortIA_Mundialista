"""
api/main.py
FastAPI application entry point para el TortIA Mundialista Prediction Engine.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger

from config import get_settings
from api.routers import predictions, tournament, teams
from api.dependencies import ModelRegistry


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga modelos al arrancar, libera al cerrar."""
    logger.info("🚀 TortIA Mundialista API arrancando...")
    artifacts_dir = Path(settings.model_dir)
    if artifacts_dir.exists():
        try:
            ModelRegistry.load(artifacts_dir)
            logger.success("✅ Modelos cargados desde artifacts/")
        except Exception as e:
            logger.warning(f"⚠️  No se pudieron cargar modelos: {e}. Usando mock predictor.")
    else:
        logger.warning("⚠️  artifacts/ no existe. Corre scripts/train.py primero.")
    yield
    logger.info("👋 API cerrando.")


app = FastAPI(
    title="TortIA Mundialista — WC2026 Prediction Engine",
    description="Motor de predicción en tiempo real para la Copa del Mundo 2026. "
                "Match outcomes, exact scores y bracket probabilities.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(predictions.router, prefix="/predict", tags=["predictions"])
app.include_router(tournament.router, prefix="/tournament", tags=["tournament"])
app.include_router(teams.router, prefix="/teams", tags=["teams"])


@app.get("/", tags=["health"])
def root():
    return {
        "service": "TortIA Mundialista",
        "version": "1.0.0",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health():
    return {
        "status": "ok",
        "models_loaded": ModelRegistry.is_loaded(),
        "environment": settings.environment,
    }
