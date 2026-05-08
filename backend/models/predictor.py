"""
models/predictor.py
HybridPredictor: ensemble de Poisson + XGBoost con blend configurable.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from models.poisson import DixonColesPoisson
from models.xgb_classifier import XGBOutcomeClassifier
from etl.features import FEATURE_COLS


class HybridPredictor:
    """
    Predictor final que combina:
      - DixonColesPoisson  → distribución de marcadores (9×9 matrix)
      - XGBOutcomeClassifier → probabilidades W/D/L contextuales

    Blend: P_final = α × P_xgb + (1-α) × P_poisson
    α = 0.55 (tuneado en Copa América 2024 + Euro 2024 out-of-sample)
    """

    def __init__(
        self,
        poisson_model: DixonColesPoisson,
        xgb_model: XGBOutcomeClassifier,
        alpha: float = 0.55,
    ):
        self.poisson = poisson_model
        self.xgb = xgb_model
        self.alpha = alpha

    def predict(
        self,
        home: str,
        away: str,
        features: pd.DataFrame,
        neutral: bool = False,
    ) -> dict:
        """
        Predicción completa de un partido.

        Returns:
            dict con outcome_probs, most_likely_score, top_5_scorelines,
            expected_goals, confidence_level.
        """
        # 1) Matriz de probabilidades de marcador (Poisson)
        matrix = self.poisson.predict_matrix(home, away, neutral=neutral)

        p_home_poi = float(np.tril(matrix, -1).sum())
        p_draw_poi = float(np.trace(matrix))
        p_away_poi = float(np.triu(matrix, 1).sum())

        # 2) Probabilidades XGBoost [away, draw, home]
        xgb_proba = self.xgb.predict_proba(features)[0]
        p_away_xgb, p_draw_xgb, p_home_xgb = float(xgb_proba[0]), float(xgb_proba[1]), float(xgb_proba[2])

        # 3) Blend
        a = self.alpha
        p_home = a * p_home_xgb + (1 - a) * p_home_poi
        p_draw = a * p_draw_xgb + (1 - a) * p_draw_poi
        p_away = a * p_away_xgb + (1 - a) * p_away_poi

        # Renormalizar por si hay drift numérico
        total = p_home + p_draw + p_away
        p_home /= total
        p_draw /= total
        p_away /= total

        # 4) Marcador más probable
        flat_idx = int(np.argmax(matrix))
        most_likely_hg = flat_idx // matrix.shape[1]
        most_likely_ag = flat_idx % matrix.shape[1]

        # 5) Top-5 marcadores
        flat = matrix.flatten()
        top5_idx = np.argsort(flat)[::-1][:5]
        top5 = [
            {
                "score": f"{i // matrix.shape[1]}-{i % matrix.shape[1]}",
                "probability": round(float(flat[i]) * 100, 2),
            }
            for i in top5_idx
        ]

        # 6) Expected goals
        goals_range = np.arange(matrix.shape[0])
        xg_h = float(np.sum(goals_range * matrix.sum(axis=1)))
        xg_a = float(np.sum(goals_range * matrix.sum(axis=0)))

        # 7) Confianza (basada en entropía de la distribución)
        max_p = max(p_home, p_draw, p_away)
        confidence = "high" if max_p > 0.55 else ("medium" if max_p > 0.42 else "low")

        return {
            "home_team": home,
            "away_team": away,
            "outcome_probs": {
                "home_win": round(p_home * 100, 2),
                "draw": round(p_draw * 100, 2),
                "away_win": round(p_away * 100, 2),
            },
            "most_likely_score": f"{most_likely_hg}-{most_likely_ag}",
            "top_5_scorelines": top5,
            "expected_goals": {
                "home": round(xg_h, 2),
                "away": round(xg_a, 2),
            },
            "confidence": confidence,
            "model_weights": {
                "xgb_alpha": self.alpha,
                "poisson_alpha": round(1 - self.alpha, 2),
            },
        }

    def predict_knockout(
        self,
        home: str,
        away: str,
        features: pd.DataFrame,
    ) -> dict:
        """
        Predicción para partidos de eliminatoria (sin empate en 90min).
        Ajusta las probabilidades para redistribuir el empate 50/50 + factor Elo.
        """
        result = self.predict(home, away, features, neutral=True)
        probs = result["outcome_probs"]

        draw_p = probs["draw"] / 100
        elo_diff = float(features.get("elo_diff", pd.Series([0])).iloc[0])
        elo_factor = 1 / (1 + 10 ** (-elo_diff / 400))  # [0,1] → ventaja home en penalties

        home_pen_share = 0.5 + 0.05 * (elo_factor - 0.5)  # pequeño sesgo Elo

        result["outcome_probs"]["home_win_after_penalties"] = round(
            (probs["home_win"] / 100 + draw_p * home_pen_share) * 100, 2
        )
        result["outcome_probs"]["away_win_after_penalties"] = round(
            (probs["away_win"] / 100 + draw_p * (1 - home_pen_share)) * 100, 2
        )
        result["includes_extra_time"] = True
        return result

    @classmethod
    def load(cls, artifacts_dir: str | Path, alpha: float = 0.55) -> "HybridPredictor":
        p = Path(artifacts_dir)
        poisson = DixonColesPoisson.load(p / "poisson_model.pkl")
        xgb = XGBOutcomeClassifier.load(p / "xgb_outcome.pkl")
        logger.info(f"HybridPredictor loaded from {p}")
        return cls(poisson, xgb, alpha=alpha)
