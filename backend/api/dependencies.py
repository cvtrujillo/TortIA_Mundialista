"""
api/dependencies.py
Singleton ModelRegistry para inyección de dependencias en FastAPI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger

from models.predictor import HybridPredictor
from models.poisson import DixonColesPoisson
from models.xgb_classifier import XGBOutcomeClassifier
from config import get_settings


class ModelRegistry:
    """Registro global de modelos (singleton thread-safe via module import)."""

    _predictor: Optional[HybridPredictor] = None

    @classmethod
    def load(cls, artifacts_dir: Path) -> None:
        settings = get_settings()
        cls._predictor = HybridPredictor.load(artifacts_dir, alpha=settings.ensemble_alpha)
        logger.info("ModelRegistry: predictor cargado.")

    @classmethod
    def get_predictor(cls) -> HybridPredictor:
        if cls._predictor is None:
            raise RuntimeError(
                "Modelos no cargados. Corre scripts/train.py y reinicia el servidor."
            )
        return cls._predictor

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._predictor is not None


def get_predictor() -> HybridPredictor:
    """FastAPI Depends helper."""
    return ModelRegistry.get_predictor()
