"""
etl/features.py
Feature engineering: Elo, momentum, altitud, fatiga, variables contextuales.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

FEATURE_COLS = [
    "elo_diff",
    "elo_home",
    "elo_away",
    "home_last5_ppg",
    "away_last5_ppg",
    "home_xg_avg_last5",
    "away_xg_avg_last5",
    "home_xgc_avg_last5",   # xG concedido
    "away_xgc_avg_last5",
    "altitude_m",
    "altitude_boost",
    "rest_diff",
    "travel_penalty_away",
    "h2h_home_winrate",
    "home_goals_avg_last5",
    "away_goals_avg_last5",
    "home_goals_conceded_avg_last5",
    "away_goals_conceded_avg_last5",
    "neutral",
]


class FeatureEngineer:
    """
    Construye el feature matrix completo a partir del DataFrame de partidos raw.
    Todos los features son lag-safe (solo usan datos previos al partido).
    """

    ELO_K = 32
    ELO_INITIAL = 1500
    ALTITUDE_INFLECTION = 500   # m — punto de inflexión del sigmoid
    ALTITUDE_SCALE = 0.001
    TRAVEL_NORMALIZATION = 10_000  # km

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Building features...")
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Labels (solo para entrenamiento — no disponibles en predicción)
        df = self._add_outcome_label(df)

        # Elo rolling
        df = self._compute_elo(df)

        # Rolling stats (window=5 partidos)
        df = self._rolling_team_stats(df, window=5)

        # Contextuales
        df = self._altitude_features(df)
        df = self._rest_features(df)
        df = self._h2h_features(df)

        # Travel penalty (si existe columna)
        if "travel_km_away" not in df.columns:
            df["travel_km_away"] = 0.0
        df["travel_penalty_away"] = np.clip(
            df["travel_km_away"] / self.TRAVEL_NORMALIZATION, 0, 0.5
        )

        if "neutral" not in df.columns:
            df["neutral"] = False
        df["neutral"] = df["neutral"].astype(int)

        logger.success(f"Features built: {df.shape[1]} columnas, {len(df)} filas")
        return df

    # ── Elo ───────────────────────────────────────────────────────────────────

    def _compute_elo(self, df: pd.DataFrame) -> pd.DataFrame:
        ratings: dict[str, float] = {}
        elo_home, elo_away = [], []

        for _, row in df.iterrows():
            h, a = row["home_team"], row["away_team"]
            rh = ratings.get(h, self.ELO_INITIAL)
            ra = ratings.get(a, self.ELO_INITIAL)
            elo_home.append(rh)
            elo_away.append(ra)

            hg = row.get("home_goals")
            ag = row.get("away_goals")
            if pd.notna(hg) and pd.notna(ag):
                exp_h = 1 / (1 + 10 ** ((ra - rh) / 400))
                actual = 1.0 if hg > ag else (0.5 if hg == ag else 0.0)
                ratings[h] = rh + self.ELO_K * (actual - exp_h)
                ratings[a] = ra + self.ELO_K * ((1 - actual) - (1 - exp_h))

        df["elo_home"] = elo_home
        df["elo_away"] = elo_away
        df["elo_diff"] = df["elo_home"] - df["elo_away"]
        return df

    # ── Rolling stats ─────────────────────────────────────────────────────────

    def _rolling_team_stats(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Calcula rolling PPG, xG, goles para cada equipo usando solo partidos anteriores.
        Maneja tanto partidos como local como visitante.
        """
        team_history: dict[str, list[dict]] = {}

        cols = [
            "home_last5_ppg", "away_last5_ppg",
            "home_xg_avg_last5", "away_xg_avg_last5",
            "home_xgc_avg_last5", "away_xgc_avg_last5",
            "home_goals_avg_last5", "away_goals_avg_last5",
            "home_goals_conceded_avg_last5", "away_goals_conceded_avg_last5",
        ]
        for c in cols:
            df[c] = np.nan

        for idx, row in df.iterrows():
            h, a = row["home_team"], row["away_team"]

            for side, team in [("home", h), ("away", a)]:
                hist = team_history.get(team, [])
                last_n = hist[-window:] if len(hist) >= window else hist

                if last_n:
                    df.at[idx, f"{side}_last5_ppg"] = np.mean([r["pts"] for r in last_n])
                    df.at[idx, f"{side}_xg_avg_last5"] = np.nanmean([r["xg_scored"] for r in last_n])
                    df.at[idx, f"{side}_xgc_avg_last5"] = np.nanmean([r["xg_conceded"] for r in last_n])
                    df.at[idx, f"{side}_goals_avg_last5"] = np.mean([r["goals_scored"] for r in last_n])
                    df.at[idx, f"{side}_goals_conceded_avg_last5"] = np.mean([r["goals_conceded"] for r in last_n])
                else:
                    df.at[idx, f"{side}_last5_ppg"] = 1.5
                    df.at[idx, f"{side}_xg_avg_last5"] = 1.2
                    df.at[idx, f"{side}_xgc_avg_last5"] = 1.2
                    df.at[idx, f"{side}_goals_avg_last5"] = 1.3
                    df.at[idx, f"{side}_goals_conceded_avg_last5"] = 1.3

            # Actualizar historial solo si el partido terminó
            hg = row.get("home_goals")
            ag = row.get("away_goals")
            if pd.notna(hg) and pd.notna(ag):
                hg, ag = int(hg), int(ag)
                pts_h = 3 if hg > ag else (1 if hg == ag else 0)
                pts_a = 3 if ag > hg else (1 if hg == ag else 0)
                xg_h = row.get("home_xg") or hg
                xg_a = row.get("away_xg") or ag

                for team, gs, gc, xgs, xgc, pts in [
                    (h, hg, ag, xg_h, xg_a, pts_h),
                    (a, ag, hg, xg_a, xg_h, pts_a),
                ]:
                    team_history.setdefault(team, []).append({
                        "goals_scored": gs,
                        "goals_conceded": gc,
                        "xg_scored": xgs,
                        "xg_conceded": xgc,
                        "pts": pts,
                    })

        return df

    # ── Altitud ───────────────────────────────────────────────────────────────

    def _altitude_features(self, df: pd.DataFrame) -> pd.DataFrame:
        altitude_map = {
            "Mexico City": 2240, "Guadalajara": 1566, "Monterrey": 538,
            "Dallas": 139, "Los Angeles": 71, "New York": 10,
            "Seattle": 20, "San Francisco": 16, "Boston": 9,
            "Miami": 2, "Atlanta": 320, "Kansas City": 304,
            "Toronto": 76, "Vancouver": 70,
        }
        if "venue" in df.columns:
            df["altitude_m"] = df["venue"].map(altitude_map).fillna(50)
        else:
            df["altitude_m"] = 50.0

        df["altitude_boost"] = 1 / (
            1 + np.exp(-self.ALTITUDE_SCALE * (df["altitude_m"] - self.ALTITUDE_INFLECTION))
        )
        return df

    # ── Descanso ──────────────────────────────────────────────────────────────

    def _rest_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "rest_days_home" not in df.columns:
            df["rest_days_home"] = 4
        if "rest_days_away" not in df.columns:
            df["rest_days_away"] = 4
        df["rest_diff"] = df["rest_days_home"] - df["rest_days_away"]
        return df

    # ── H2H ───────────────────────────────────────────────────────────────────

    def _h2h_features(self, df: pd.DataFrame) -> pd.DataFrame:
        h2h_cache: dict[tuple, list] = {}
        h2h_rates = []

        for idx, row in df.iterrows():
            h, a = row["home_team"], row["away_team"]
            key = tuple(sorted([h, a]))
            history = h2h_cache.get(key, [])
            last5 = history[-5:]

            if not last5:
                h2h_rates.append(0.5)
            else:
                home_wins = sum(
                    1 for r in last5
                    if (r["home"] == h and r["hg"] > r["ag"]) or
                       (r["away"] == h and r["ag"] > r["hg"])
                )
                h2h_rates.append(home_wins / len(last5))

            hg = row.get("home_goals")
            ag = row.get("away_goals")
            if pd.notna(hg) and pd.notna(ag):
                h2h_cache.setdefault(key, []).append({"home": h, "away": a, "hg": hg, "ag": ag})

        df["h2h_home_winrate"] = h2h_rates
        return df

    # ── Labels ────────────────────────────────────────────────────────────────

    @staticmethod
    def _add_outcome_label(df: pd.DataFrame) -> pd.DataFrame:
        """0=away win, 1=draw, 2=home win"""
        def label(row):
            hg, ag = row.get("home_goals"), row.get("away_goals")
            if pd.isna(hg) or pd.isna(ag):
                return np.nan
            if hg > ag:
                return 2
            if hg == ag:
                return 1
            return 0

        df["outcome"] = df.apply(label, axis=1)
        return df
