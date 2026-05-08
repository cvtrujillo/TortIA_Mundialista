code = """from __future__ import annotations
import time
import pandas as pd
import requests
from loguru import logger


class FootballDataSource:
    BASE_URL = "https://api.football-data.org/v4"
    RATE_LIMIT_DELAY = 6.5

    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers.update({"X-Auth-Token": token})
        self._last_request = 0.0

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request = time.monotonic()

    def _get(self, path, params=None):
        self._throttle()
        resp = self.session.get(f"{self.BASE_URL}/{path}", params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def fetch_matches(self, competition_id, season):
        try:
            data = self._get(
                f"competitions/{competition_id}/matches",
                params={"season": season, "status": "FINISHED"}
            )
            matches = data.get("matches", [])
            if not matches:
                return pd.DataFrame()
            return pd.DataFrame([self._normalize(m, competition_id) for m in matches])
        except Exception as e:
            logger.warning(f"  {competition_id}/{season} fallo: {e}")
            return pd.DataFrame()

    @staticmethod
    def _normalize(m, competition):
        ft = m.get("score", {}).get("fullTime", {})
        return {
            "match_id": str(m.get("id", "")),
            "home_team": m.get("homeTeam", {}).get("name", ""),
            "home_team_id": m.get("homeTeam", {}).get("id"),
            "away_team": m.get("awayTeam", {}).get("name", ""),
            "away_team_id": m.get("awayTeam", {}).get("id"),
            "home_goals": ft.get("home"),
            "away_goals": ft.get("away"),
            "date": m.get("utcDate", "")[:10],
            "competition": competition,
            "stage": m.get("stage", "REGULAR_SEASON"),
            "status": m.get("status", ""),
            "venue": m.get("venue"),
            "neutral": False,
            "home_xg": None,
            "away_xg": None,
        }
"""

with open("etl/sources/football_data.py", "w", encoding="utf-8") as f:
    f.write(code)
print("OK - archivo sobreescrito")