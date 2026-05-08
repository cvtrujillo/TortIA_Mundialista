"""
api/schemas.py
Todos los modelos Pydantic para request/response de la API.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ── Match Prediction ──────────────────────────────────────────────────────────

class MatchPredictionRequest(BaseModel):
    home_team: str = Field(..., example="Brazil")
    away_team: str = Field(..., example="France")
    venue: Optional[str] = Field(None, example="Mexico City")
    stage: str = Field("group", example="group")
    home_rest_days: int = Field(4, ge=0, le=30)
    away_rest_days: int = Field(4, ge=0, le=30)
    away_travel_km: float = Field(0.0, ge=0.0)
    neutral_venue: bool = Field(False)


class ScorelineProbability(BaseModel):
    score: str
    probability: float


class MatchPredictionResponse(BaseModel):
    home_team: str
    away_team: str
    outcome_probs: dict[str, float]
    most_likely_score: str
    top_5_scorelines: list[ScorelineProbability]
    expected_goals: dict[str, float]
    confidence: str
    model_weights: dict[str, float]
    computed_at_ms: float


# ── Knockout Prediction ───────────────────────────────────────────────────────

class KnockoutPredictionResponse(MatchPredictionResponse):
    includes_extra_time: bool = True
    outcome_probs: dict[str, float]  # incluye home/away_win_after_penalties


# ── Tournament Simulation ─────────────────────────────────────────────────────

class SimulationRequest(BaseModel):
    n_simulations: int = Field(10_000, ge=1_000, le=100_000)
    n_workers: int = Field(4, ge=1, le=8)


class TeamSimResult(BaseModel):
    team: str
    win_pct: float
    final_pct: float
    sf_pct: float
    qf_pct: float
    r16_pct: float


# ── Teams ─────────────────────────────────────────────────────────────────────

class TeamStatsResponse(BaseModel):
    team: str
    elo: float
    last5_ppg: float
    xg_avg_last5: float
    xgc_avg_last5: float
    goals_avg_last5: float
    goals_conceded_avg_last5: float
    attack_strength: Optional[float] = None
    defense_strength: Optional[float] = None


# ── Live Update ───────────────────────────────────────────────────────────────

class LiveResultRequest(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    home_goals: int = Field(..., ge=0)
    away_goals: int = Field(..., ge=0)
    competition: str = Field("WC2026")
