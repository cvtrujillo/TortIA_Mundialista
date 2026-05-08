"""
api/routers/tournament.py
Endpoints de simulación Monte Carlo del bracket WC2026.
"""
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Annotated

from api.dependencies import get_predictor
from api.schemas import SimulationRequest, TeamSimResult
from models.predictor import HybridPredictor
from simulation.monte_carlo import run_tournament_simulation, WC2026_GROUPS

router = APIRouter()


def _default_features() -> pd.DataFrame:
    """Features por defecto para simulaciones (equipos desconocidos)."""
    return pd.DataFrame([{
        "elo_diff": 0.0, "elo_home": 1500.0, "elo_away": 1500.0,
        "home_last5_ppg": 1.7, "away_last5_ppg": 1.7,
        "home_xg_avg_last5": 1.3, "away_xg_avg_last5": 1.3,
        "home_xgc_avg_last5": 1.3, "away_xgc_avg_last5": 1.3,
        "altitude_m": 50.0, "altitude_boost": 0.5,
        "rest_diff": 0.0, "travel_penalty_away": 0.0,
        "h2h_home_winrate": 0.5,
        "home_goals_avg_last5": 1.5, "away_goals_avg_last5": 1.5,
        "home_goals_conceded_avg_last5": 1.2, "away_goals_conceded_avg_last5": 1.2,
        "neutral": 1,
    }])


@router.post("/simulate", response_model=list[TeamSimResult])
def simulate_tournament(
    req: SimulationRequest,
    predictor: Annotated[HybridPredictor, Depends(get_predictor)],
):
    """
    Corre N simulaciones Monte Carlo del torneo completo WC2026.
    Devuelve probabilidad de campeonar, llegar a final, SF, QF, R16 por equipo.
    ⚠️  Para N > 10k puede tomar 30-60s. Considera usar una cola en prod.
    """
    try:
        results = run_tournament_simulation(
            groups=WC2026_GROUPS,
            predictor=predictor,
            default_features=_default_features(),
            n_simulations=req.n_simulations,
            n_workers=req.n_workers,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return [
        TeamSimResult(
            team=row["team"],
            win_pct=row["win_pct"],
            final_pct=row["final_pct"],
            sf_pct=row["sf_pct"],
            qf_pct=row["qf_pct"],
            r16_pct=row["r16_pct"],
        )
        for _, row in results.iterrows()
    ]


@router.get("/groups")
def get_groups():
    """Devuelve la configuración de grupos WC2026."""
    return WC2026_GROUPS


@router.get("/bracket-placeholder")
def get_bracket_placeholder():
    """Estructura de bracket para el frontend (antes del torneo)."""
    return {
        "rounds": ["R32", "R16", "QF", "SF", "Final"],
        "groups": WC2026_GROUPS,
        "total_teams": sum(len(v) for v in WC2026_GROUPS.values()),
    }
