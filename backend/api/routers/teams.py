"""
api/routers/teams.py
Endpoints de estadísticas y rankings de equipos.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from api.dependencies import get_predictor
from api.schemas import TeamStatsResponse
from models.predictor import HybridPredictor

router = APIRouter()

# Mock stats — en prod: consultar feature store Redis/DuckDB
_MOCK_TEAM_STATS = {
    "Brazil":      {"elo": 2092, "last5_ppg": 2.2, "xg_avg_last5": 2.1, "xgc_avg_last5": 0.8, "goals_avg_last5": 2.0, "goals_conceded_avg_last5": 0.9},
    "France":      {"elo": 2003, "last5_ppg": 2.1, "xg_avg_last5": 1.9, "xgc_avg_last5": 0.9, "goals_avg_last5": 1.8, "goals_conceded_avg_last5": 1.0},
    "Argentina":   {"elo": 2145, "last5_ppg": 2.4, "xg_avg_last5": 2.3, "xgc_avg_last5": 0.7, "goals_avg_last5": 2.2, "goals_conceded_avg_last5": 0.8},
    "Spain":       {"elo": 1987, "last5_ppg": 2.0, "xg_avg_last5": 1.8, "xgc_avg_last5": 1.0, "goals_avg_last5": 1.7, "goals_conceded_avg_last5": 1.1},
    "England":     {"elo": 1942, "last5_ppg": 1.9, "xg_avg_last5": 1.7, "xgc_avg_last5": 1.1, "goals_avg_last5": 1.6, "goals_conceded_avg_last5": 1.0},
    "Germany":     {"elo": 1918, "last5_ppg": 1.8, "xg_avg_last5": 1.7, "xgc_avg_last5": 1.2, "goals_avg_last5": 1.7, "goals_conceded_avg_last5": 1.2},
    "Portugal":    {"elo": 1958, "last5_ppg": 2.0, "xg_avg_last5": 1.9, "xgc_avg_last5": 1.0, "goals_avg_last5": 1.9, "goals_conceded_avg_last5": 1.0},
    "Netherlands": {"elo": 1901, "last5_ppg": 1.8, "xg_avg_last5": 1.6, "xgc_avg_last5": 1.2, "goals_avg_last5": 1.6, "goals_conceded_avg_last5": 1.1},
    "Mexico":      {"elo": 1742, "last5_ppg": 1.6, "xg_avg_last5": 1.4, "xgc_avg_last5": 1.3, "goals_avg_last5": 1.4, "goals_conceded_avg_last5": 1.2},
    "USA":         {"elo": 1698, "last5_ppg": 1.5, "xg_avg_last5": 1.3, "xgc_avg_last5": 1.4, "goals_avg_last5": 1.3, "goals_conceded_avg_last5": 1.3},
    "Colombia":    {"elo": 1820, "last5_ppg": 1.9, "xg_avg_last5": 1.7, "xgc_avg_last5": 1.0, "goals_avg_last5": 1.8, "goals_conceded_avg_last5": 1.0},
    "Morocco":     {"elo": 1788, "last5_ppg": 1.7, "xg_avg_last5": 1.3, "xgc_avg_last5": 0.9, "goals_avg_last5": 1.2, "goals_conceded_avg_last5": 0.8},
}


@router.get("/{team_name}/stats", response_model=TeamStatsResponse)
def get_team_stats(
    team_name: str,
    predictor: Annotated[HybridPredictor, Depends(get_predictor)],
):
    stats = _MOCK_TEAM_STATS.get(team_name)
    if not stats:
        raise HTTPException(status_code=404, detail=f"Equipo '{team_name}' no encontrado.")

    return TeamStatsResponse(
        team=team_name,
        attack_strength=predictor.poisson.attack.get(team_name),
        defense_strength=predictor.poisson.defense.get(team_name),
        **stats,
    )


@router.get("/rankings/elo")
def get_elo_rankings(predictor: Annotated[HybridPredictor, Depends(get_predictor)]):
    """Ranking de todos los equipos por Elo."""
    rankings = sorted(
        _MOCK_TEAM_STATS.items(),
        key=lambda x: x[1]["elo"],
        reverse=True,
    )
    return [
        {"rank": i + 1, "team": team, "elo": stats["elo"]}
        for i, (team, stats) in enumerate(rankings)
    ]


@router.get("/")
def list_teams():
    return {"teams": sorted(_MOCK_TEAM_STATS.keys())}
