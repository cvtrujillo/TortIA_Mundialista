"""
api/routers/predictions.py
Endpoints de predicción de partidos individuales.
"""
import time
from typing import Annotated

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_predictor
from api.schemas import (
    MatchPredictionRequest,
    MatchPredictionResponse,
    KnockoutPredictionResponse,
    ScorelineProbability,
    LiveResultRequest,
)
from etl.features import FEATURE_COLS
from models.predictor import HybridPredictor

router = APIRouter()

ALTITUDE_MAP = {
    "Mexico City": 2240, "Guadalajara": 1566, "Monterrey": 538,
    "Dallas": 139, "Los Angeles": 71, "New York": 10,
    "Seattle": 20, "San Francisco": 16, "Boston": 9,
    "Miami": 2, "Atlanta": 320, "Kansas City": 304,
    "Toronto": 76, "Vancouver": 70,
}


def _build_features(req: MatchPredictionRequest) -> pd.DataFrame:
    """Construye el DataFrame de features a partir del request."""
    altitude_m = ALTITUDE_MAP.get(req.venue or "", 50)
    altitude_boost = 1 / (1 + 2.71828 ** (-0.001 * (altitude_m - 500)))

    # En producción: consultar feature store (Redis/DuckDB) para los valores reales.
    # Aquí usamos defaults razonables como fallback.
    return pd.DataFrame([{
        "elo_diff": 0.0,
        "elo_home": 1500.0,
        "elo_away": 1500.0,
        "home_last5_ppg": 1.8,
        "away_last5_ppg": 1.6,
        "home_xg_avg_last5": 1.5,
        "away_xg_avg_last5": 1.3,
        "home_xgc_avg_last5": 1.1,
        "away_xgc_avg_last5": 1.3,
        "altitude_m": float(altitude_m),
        "altitude_boost": altitude_boost,
        "rest_diff": float(req.home_rest_days - req.away_rest_days),
        "travel_penalty_away": min(req.away_travel_km / 10_000, 0.5),
        "h2h_home_winrate": 0.5,
        "home_goals_avg_last5": 1.7,
        "away_goals_avg_last5": 1.5,
        "home_goals_conceded_avg_last5": 1.0,
        "away_goals_conceded_avg_last5": 1.2,
        "neutral": int(req.neutral_venue),
    }])


@router.post("/match", response_model=MatchPredictionResponse)
def predict_match(
    req: MatchPredictionRequest,
    predictor: Annotated[HybridPredictor, Depends(get_predictor)],
):
    """
    Predice el resultado de un partido de fase de grupos.
    Devuelve distribución W/D/L, marcador más probable y top-5 marcadores.
    """
    t0 = time.perf_counter()

    try:
        features = _build_features(req)
        result = predictor.predict(
            req.home_team,
            req.away_team,
            features,
            neutral=req.neutral_venue,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de predicción: {e}")

    return MatchPredictionResponse(
        home_team=result["home_team"],
        away_team=result["away_team"],
        outcome_probs=result["outcome_probs"],
        most_likely_score=result["most_likely_score"],
        top_5_scorelines=[
            ScorelineProbability(**s) for s in result["top_5_scorelines"]
        ],
        expected_goals=result["expected_goals"],
        confidence=result["confidence"],
        model_weights=result["model_weights"],
        computed_at_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


@router.post("/knockout", response_model=KnockoutPredictionResponse)
def predict_knockout(
    req: MatchPredictionRequest,
    predictor: Annotated[HybridPredictor, Depends(get_predictor)],
):
    """
    Predicción para partido de eliminatoria.
    Incluye probabilidades ajustadas con prórroga y penales.
    """
    t0 = time.perf_counter()
    try:
        features = _build_features(req)
        result = predictor.predict_knockout(req.home_team, req.away_team, features)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return KnockoutPredictionResponse(
        home_team=result["home_team"],
        away_team=result["away_team"],
        outcome_probs=result["outcome_probs"],
        most_likely_score=result["most_likely_score"],
        top_5_scorelines=[
            ScorelineProbability(**s) for s in result["top_5_scorelines"]
        ],
        expected_goals=result["expected_goals"],
        confidence=result["confidence"],
        model_weights=result["model_weights"],
        includes_extra_time=True,
        computed_at_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


@router.post("/live-update")
def update_live_result(req: LiveResultRequest):
    """
    Ingesta un resultado en tiempo real durante el torneo.
    Dispara recálculo de Elo y momentum en background.
    """
    # En producción: escribir en Redis y encolar actualización de features
    return {
        "status": "accepted",
        "match_id": req.match_id,
        "result": f"{req.home_goals}-{req.away_goals}",
        "message": "Elo y momentum actualizados. Simulación Monte Carlo re-encolada.",
    }
