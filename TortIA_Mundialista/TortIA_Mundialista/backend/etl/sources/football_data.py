"""
etl/sources/football_data.py
Wrapper para Football-Data.org API v4 (fuente primaria, gratuita).
"""
from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


class FootballDataSource:
    BASE_URL = "https://api.football-data.org/v4"
    RATE_LIMIT_DELAY = 6.5  # free tier: 10 req/min → 1 cada 6s

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "X-Auth-Token": token,
            "User-Agent": "TortIA-Mundialista/1.0",
        })
        self._last_request = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request = time.monotonic()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def _get(self, path: str, params: dict | None = None) -> Any:
        self._throttle()
        url = f"{self.BASE_URL}/{path}"
        resp = self.session.get(url, params=params, timeout=20)
        if resp.status_code == 429:
            logger.warning("Rate limit hit — esperando 60s")
            time.sleep(60)
            raise RuntimeError("Rate limit")
        resp.raise_for_status()
        return resp.json()

    def fetch_matches(
        self,
        competition_id: str,
        date_from: str,
        date_to: str,
        status: str = "FINISHED",
    ) -> pd.DataFrame:
        data = self._get(
            f"competitions/{competition_id}/matches",
            params={"dateFrom": date_from, "dateTo": date_to, "status": status},
        )
        matches = data.get("matches", [])
        if not matches:
            return pd.DataFrame()
        rows = [self._normalize(m, competition_id) for m in matches]
        return pd.DataFrame(rows)

    def fetch_team_squad(self, team_id: int) -> pd.DataFrame:
        data = self._get(f"teams/{team_id}")
        squad = data.get("squad", [])
        return pd.DataFrame(squad)

    def fetch_standings(self, competition_id: str) -> pd.DataFrame:
        data = self._get(f"competitions/{competition_id}/standings")
        rows = []
        for standing in data.get("standings", []):
            for entry in standing.get("table", []):
                rows.append({
                    "team": entry["team"]["name"],
                    "team_id": entry["team"]["id"],
                    "played": entry["playedGames"],
                    "won": entry["won"],
                    "draw": entry["draw"],
                    "lost": entry["lost"],
                    "goals_for": entry["goalsFor"],
                    "goals_against": entry["goalsAgainst"],
                    "points": entry["points"],
                })
        return pd.DataFrame(rows)

    @staticmethod
    def _normalize(m: dict, competition: str) -> dict:
        score = m.get("score", {})
        ft = score.get("fullTime", {})
        home_team = m.get("homeTeam", {})
        away_team = m.get("awayTeam", {})
        return {
            "match_id": str(m.get("id", "")),
            "home_team": home_team.get("name", ""),
            "home_team_id": home_team.get("id"),
            "away_team": away_team.get("name", ""),
            "away_team_id": away_team.get("id"),
            "home_goals": ft.get("home"),
            "away_goals": ft.get("away"),
            "date": m.get("utcDate", "")[:10],
            "competition": competition,
            "stage": m.get("stage", "REGULAR_SEASON"),
            "status": m.get("status", ""),
            "venue": m.get("venue"),
            "neutral": False,
            # xG será enriquecido por FBref
            "home_xg": None,
            "away_xg": None,
        }
