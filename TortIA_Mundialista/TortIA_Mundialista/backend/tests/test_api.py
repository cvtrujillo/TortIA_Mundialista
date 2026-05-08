"""
tests/test_api.py
Tests de integración para los endpoints FastAPI.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import numpy as np

from api.main import app
from api.dependencies import ModelRegistry


@pytest.fixture
def mock_predictor():
    """Mock del HybridPredictor para tests sin modelos reales."""
    pred = MagicMock()
    pred.predict.return_value = {
        "home_team": "Brazil",
        "away_team": "France",
        "outcome_probs": {"home_win": 42.5, "draw": 25.0, "away_win": 32.5},
        "most_likely_score": "1-1",
        "top_5_scorelines": [
            {"score": "1-1", "probability": 12.3},
            {"score": "2-1", "probability": 10.1},
            {"score": "1-0", "probability": 9.8},
            {"score": "2-0", "probability": 8.2},
            {"score": "0-1", "probability": 7.5},
        ],
        "expected_goals": {"home": 1.45, "away": 1.32},
        "confidence": "medium",
        "model_weights": {"xgb_alpha": 0.55, "poisson_alpha": 0.45},
    }
    pred.predict_knockout.return_value = {**pred.predict.return_value,
        "includes_extra_time": True}
    pred.poisson.attack = {"Brazil": 1.4, "France": 1.3}
    pred.poisson.defense = {"Brazil": 0.85, "France": 0.90}
    return pred


@pytest.fixture
def client(mock_predictor):
    ModelRegistry._predictor = mock_predictor
    with TestClient(app) as c:
        yield c
    ModelRegistry._predictor = None


class TestHealth:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["service"] == "TortIA Mundialista"

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["models_loaded"] is True


class TestPredictions:
    def test_predict_match_ok(self, client):
        r = client.post("/predict/match", json={
            "home_team": "Brazil",
            "away_team": "France",
            "venue": "Mexico City",
            "stage": "group",
            "home_rest_days": 4,
            "away_rest_days": 3,
            "away_travel_km": 9000.0,
            "neutral_venue": False,
        })
        assert r.status_code == 200
        body = r.json()
        assert "outcome_probs" in body
        assert "home_win" in body["outcome_probs"]
        assert abs(sum(body["outcome_probs"].values()) - 100.0) < 1.0
        assert len(body["top_5_scorelines"]) == 5

    def test_predict_match_missing_fields(self, client):
        r = client.post("/predict/match", json={})
        assert r.status_code == 422

    def test_predict_knockout(self, client):
        r = client.post("/predict/knockout", json={
            "home_team": "Argentina",
            "away_team": "France",
            "neutral_venue": True,
        })
        assert r.status_code == 200
        assert r.json()["includes_extra_time"] is True

    def test_live_update(self, client):
        r = client.post("/predict/live-update", json={
            "match_id": "wc2026_001",
            "home_team": "Brazil",
            "away_team": "France",
            "home_goals": 2,
            "away_goals": 1,
            "competition": "WC2026",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"


class TestTeams:
    def test_get_team_stats(self, client):
        r = client.get("/teams/Brazil/stats")
        assert r.status_code == 200
        assert r.json()["team"] == "Brazil"
        assert "elo" in r.json()

    def test_team_not_found(self, client):
        r = client.get("/teams/Wakanda/stats")
        assert r.status_code == 404

    def test_elo_rankings(self, client):
        r = client.get("/teams/rankings/elo")
        assert r.status_code == 200
        rankings = r.json()
        assert isinstance(rankings, list)
        assert len(rankings) > 0
        assert rankings[0]["rank"] == 1


class TestTournament:
    def test_get_groups(self, client):
        r = client.get("/tournament/groups")
        assert r.status_code == 200
        groups = r.json()
        assert isinstance(groups, dict)
        assert len(groups) == 12

    def test_bracket_placeholder(self, client):
        r = client.get("/tournament/bracket-placeholder")
        assert r.status_code == 200
        assert "rounds" in r.json()
