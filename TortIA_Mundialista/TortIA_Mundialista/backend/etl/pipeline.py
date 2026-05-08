"""
etl/pipeline.py
Orquestador principal del pipeline de ingesta y feature engineering.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from etl.sources.football_data import FootballDataSource
from etl.sources.fbref import FBrefSource
from etl.features import FeatureEngineer


@dataclass
class RawMatch:
    match_id: str
    home_team: str
    away_team: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    date: str
    competition: str
    venue: Optional[str] = None
    stage: str = "regular"
    neutral: bool = False


class WorldCupETL:
    """
    Pipeline E2E: ingesta → normalización → feature engineering → Parquet.
    Soporta Football-Data.org (principal), API-Football (stats), FBref (xG).
    """

    VENUE_ALTITUDE_M: dict[str, int] = {
        "Mexico City": 2240,
        "Guadalajara": 1566,
        "Monterrey": 538,
        "Dallas": 139,
        "Los Angeles": 71,
        "New York": 10,
        "Seattle": 20,
        "San Francisco": 16,
        "Boston": 9,
        "Miami": 2,
        "Atlanta": 320,
        "Kansas City": 304,
        "Toronto": 76,
        "Vancouver": 70,
    }

    WC2026_VENUES = {
        "group_A": "Mexico City",
        "group_B": "Los Angeles",
        "group_C": "New York",
        "group_D": "Dallas",
        "group_E": "Seattle",
        "group_F": "San Francisco",
        "group_G": "Atlanta",
        "group_H": "Kansas City",
        "group_I": "Miami",
        "group_J": "Boston",
        "group_K": "Guadalajara",
        "group_L": "Toronto",
    }

    def __init__(
        self,
        football_data_token: str,
        rapidapi_key: str = "",
        output_dir: str = "data",
    ):
        self.fd_source = FootballDataSource(token=football_data_token)
        self.fbref_source = FBrefSource()
        self.feature_engineer = FeatureEngineer()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ── Ingesta ────────────────────────────────────────────────────────────────

    def ingest_historical(
        self,
        date_from: str = "2022-11-01",
        date_to: str | None = None,
    ) -> pd.DataFrame:
        """
        Descarga y normaliza partidos históricos de múltiples fuentes.
        Prioridad: Football-Data.org → FBref (xG).
        """
        date_to = date_to or datetime.today().strftime("%Y-%m-%d")
        logger.info(f"Ingesting matches from {date_from} to {date_to}")

        # 1. Resultados base desde Football-Data.org
        competitions = ["WC", "EC", "CLI", "BSA", "PD", "FL1", "BL1", "SA", "PL"]
        all_matches: list[pd.DataFrame] = []

        for comp in competitions:
            try:
                df = self.fd_source.fetch_matches(comp, date_from, date_to)
                if not df.empty:
                    all_matches.append(df)
                    logger.info(f"  {comp}: {len(df)} partidos")
            except Exception as e:
                logger.warning(f"  {comp}: error → {e}")

        if not all_matches:
            raise RuntimeError("No se pudo obtener ningún partido. Revisa el token de API.")

        base_df = pd.concat(all_matches, ignore_index=True)
        base_df = self._deduplicate(base_df)
        logger.info(f"Base dataset: {len(base_df)} partidos únicos")

        # 2. Enriquecer con xG de FBref (mejor calidad)
        base_df = self.fbref_source.enrich_with_xg(base_df)

        # 3. Feature engineering
        featured_df = self.feature_engineer.build(base_df)

        # 4. Guardar
        out_path = self.output_dir / "matches_featured.parquet"
        featured_df.to_parquet(out_path, index=False)
        logger.success(f"Saved {len(featured_df)} rows → {out_path}")

        return featured_df

    def ingest_live_result(self, match_id: str, home_goals: int, away_goals: int) -> None:
        """
        Ingesta un resultado en tiempo real durante el torneo.
        Actualiza Elo, momentum y el feature store.
        """
        logger.info(f"Live result ingested: match={match_id} {home_goals}-{away_goals}")
        # En prod: escribe en Redis y dispara recálculo de Elo
        # Ver: etl/features.py → FeatureEngineer.update_live()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
        return df.drop_duplicates(subset=["match_id"]).reset_index(drop=True)

    def get_venue_altitude(self, venue: str) -> int:
        return self.VENUE_ALTITUDE_M.get(venue, 50)
