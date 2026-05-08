"""
etl/sources/fbref.py
Scraper respetuoso de FBref (datos Statsbomb) para xG/xA.
Delay de 3s entre requests, User-Agent identificado, sin bypass de ToS.
"""
from __future__ import annotations

import time
from io import StringIO
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from loguru import logger


class FBrefSource:
    BASE_URL = "https://fbref.com"
    DELAY = 3.5  # segundos entre requests (respetar ToS)

    # Slug de equipos nacionales en FBref
    NATIONAL_TEAM_SLUGS: dict[str, str] = {
        "Argentina": "f9fddd6e",
        "France": "7a5d6b5b",
        "Brazil": "e8ef7f23",
        "England": "cfa928f3",
        "Germany": "811949e6",
        "Spain": "e6f3cd80",
        "Portugal": "bb77b8f4",
        "Netherlands": "f27f0bb8",
        "Belgium": "e4dba0fb",
        "Uruguay": "5a4e6e93",
        "Mexico": "8cec06e1",
        "USA": "7f71acff",
        "Colombia": "2ef9a17e",
        "Morocco": "361abd2d",
        "Japan": "f3f91701",
        "South Korea": "7269d35b",
        "Senegal": "eafb2e1d",
        "Ecuador": "46f9dcd0",
        "Croatia": "c3e3a82d",
        "Poland": "d6d22b84",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TortIA-Mundialista/1.0 (Research; github.com/cvtrujillo/TortIA_Mundialista)",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self._last_request = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.DELAY:
            time.sleep(self.DELAY - elapsed)
        self._last_request = time.monotonic()

    def fetch_team_shooting(self, team_name: str, season: str = "2024") -> Optional[pd.DataFrame]:
        """Scrape tabla de disparos (xG, npxG) para un equipo nacional."""
        slug = self.NATIONAL_TEAM_SLUGS.get(team_name)
        if not slug:
            logger.debug(f"FBref: no slug para {team_name}")
            return None

        url = f"{self.BASE_URL}/en/squads/{slug}/{season}/shooting/"
        self._throttle()
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"FBref fetch error ({team_name}): {e}")
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table", {"id": "stats_shooting"})
        if not table:
            logger.warning(f"FBref: no se encontró tabla de disparos para {team_name}")
            return None

        df = pd.read_html(StringIO(str(table)), header=1)[0]
        df.columns = [str(c).strip() for c in df.columns]
        df = df[df["Player"].notna() & (df["Player"] != "Player")]

        # Normalizar columnas clave
        col_map = {c: c.lower().replace(" ", "_") for c in df.columns}
        df = df.rename(columns=col_map)
        df["team"] = team_name
        df["season"] = season
        return df

    def get_team_xg_summary(self, team_name: str, season: str = "2024") -> dict:
        """Devuelve xG total y npxG total del equipo como dict."""
        df = self.fetch_team_shooting(team_name, season)
        if df is None or df.empty:
            return {"xg_total": None, "npxg_total": None, "shots_total": None}

        for xg_col in ["xg", "expected_xg", "xg_expected"]:
            if xg_col in df.columns:
                try:
                    xg_total = pd.to_numeric(df[xg_col], errors="coerce").sum()
                    return {
                        "xg_total": round(float(xg_total), 2),
                        "npxg_total": None,
                        "shots_total": int(pd.to_numeric(df.get("sh", df.get("shots", 0)), errors="coerce").sum()),
                    }
                except Exception:
                    pass
        return {"xg_total": None, "npxg_total": None, "shots_total": None}

    def enrich_with_xg(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enriquece el DataFrame base con xG de FBref donde sea posible.
        Si no hay dato, deja None (el modelo usa xG estimado como fallback).
        """
        logger.info("Enriching with FBref xG data...")
        teams = pd.unique(df[["home_team", "away_team"]].values.ravel())
        xg_cache: dict[str, dict] = {}

        for team in teams:
            xg_cache[team] = self.get_team_xg_summary(team)
            logger.debug(f"  {team}: {xg_cache[team]}")

        # Imputar xG promedio por partido (season total / matches played)
        def get_xg_per_match(team: str, n_matches: int) -> Optional[float]:
            total = xg_cache.get(team, {}).get("xg_total")
            if total is None or n_matches == 0:
                return None
            return round(total / max(n_matches, 1), 3)

        home_match_counts = df["home_team"].value_counts().to_dict()
        away_match_counts = df["away_team"].value_counts().to_dict()
        match_counts = {
            t: home_match_counts.get(t, 0) + away_match_counts.get(t, 0)
            for t in teams
        }

        if "home_xg" not in df.columns:
            df["home_xg"] = None
        if "away_xg" not in df.columns:
            df["away_xg"] = None

        mask_h = df["home_xg"].isna()
        df.loc[mask_h, "home_xg"] = df.loc[mask_h, "home_team"].map(
            lambda t: get_xg_per_match(t, match_counts.get(t, 1))
        )
        mask_a = df["away_xg"].isna()
        df.loc[mask_a, "away_xg"] = df.loc[mask_a, "away_team"].map(
            lambda t: get_xg_per_match(t, match_counts.get(t, 1))
        )

        logger.success(f"xG enrichment: {(~df['home_xg'].isna()).sum()}/{len(df)} partidos con xG")
        return df
