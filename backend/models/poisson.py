"""
models/poisson.py
Modelo Dixon-Coles bivariate Poisson para distribución de marcadores.
Estima parámetros de ataque/defensa por equipo vía MLE.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from loguru import logger
from scipy.optimize import minimize
from scipy.stats import poisson


class DixonColesPoisson:
    """
    Modelo de Poisson bivariado con corrección Dixon-Coles para marcadores bajos.

    Parámetros estimados:
      - attack[team]:  fuerza ofensiva relativa
      - defense[team]: fuerza defensiva relativa (valores bajos = mejor defensa)
      - home_adv:      ventaja de local (escalar multiplicativo)
      - rho:           correlación para corrección de marcadores bajos

    Referencia: Dixon & Coles (1997) "Modelling Association Football Scores
    and Inefficiencies in the Football Betting Market". JRSS Series C.
    """

    def __init__(self):
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}
        self.home_adv: float = 1.25
        self.rho: float = -0.13
        self.base_rate: float = 1.1
        self.teams: list[str] = []
        self.is_fitted: bool = False

    def fit(self, df: pd.DataFrame, verbose: bool = True) -> "DixonColesPoisson":
        """
        Ajusta el modelo usando MLE sobre partidos terminados.
        df requiere columnas: home_team, away_team, home_goals, away_goals.
        """
        df_fit = df.dropna(subset=["home_goals", "away_goals"]).copy()
        df_fit["home_goals"] = df_fit["home_goals"].astype(int)
        df_fit["away_goals"] = df_fit["away_goals"].astype(int)

        self.teams = sorted(
            pd.unique(df_fit[["home_team", "away_team"]].values.ravel()).tolist()
        )
        n = len(self.teams)
        team_idx = {t: i for i, t in enumerate(self.teams)}

        # x0: [attack × n, defense × n, home_adv, rho]
        x0 = np.concatenate([
            np.ones(n),          # attack
            np.ones(n),          # defense
            [1.25, -0.13],       # home_adv, rho
        ])

        bounds = (
            [(0.1, 5.0)] * n      +  # attack
            [(0.1, 5.0)] * n      +  # defense
            [(1.0, 2.0)]          +  # home_adv
            [(-0.5, 0.0)]            # rho
        )

        records = df_fit[["home_team", "away_team", "home_goals", "away_goals"]].values

        def neg_log_likelihood(params: np.ndarray) -> float:
            atk = params[:n]
            dfn = params[n:2*n]
            hfa = params[2*n]
            rho = params[2*n + 1]
            ll = 0.0
            for home, away, hg, ag in records:
                hi = team_idx.get(home)
                ai = team_idx.get(away)
                if hi is None or ai is None:
                    continue
                mu_h = atk[hi] * dfn[ai] * hfa * self.base_rate
                mu_a = atk[ai] * dfn[hi] * self.base_rate
                # Dixon-Coles low-score correction τ
                tau = self._tau(int(hg), int(ag), mu_h, mu_a, rho)
                if tau <= 0:
                    continue
                ll += (
                    poisson.logpmf(int(hg), mu_h)
                    + poisson.logpmf(int(ag), mu_a)
                    + np.log(tau)
                )
            return -ll

        logger.info(f"Fitting Dixon-Coles Poisson on {len(df_fit)} matches, {n} teams...")
        result = minimize(
            neg_log_likelihood,
            x0,
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 1000, "ftol": 1e-9},
        )

        if verbose:
            logger.info(f"Optimization: success={result.success}, loss={result.fun:.4f}")

        params = result.x
        self.attack = dict(zip(self.teams, params[:n]))
        self.defense = dict(zip(self.teams, params[n:2*n]))
        self.home_adv = float(params[2*n])
        self.rho = float(params[2*n + 1])
        self.is_fitted = True

        logger.success(
            f"Modelo ajustado. HFA={self.home_adv:.3f}, rho={self.rho:.3f}"
        )
        return self

    def predict_matrix(
        self,
        home: str,
        away: str,
        max_goals: int = 8,
        neutral: bool = False,
    ) -> np.ndarray:
        """
        Devuelve matriz de probabilidades (max_goals+1) × (max_goals+1).
        matrix[h_goals, a_goals] = P(home scores h_goals AND away scores a_goals).
        """
        if not self.is_fitted:
            raise RuntimeError("Modelo no ajustado. Llama a fit() primero.")

        atk_h = self.attack.get(home, 1.0)
        dfn_h = self.defense.get(home, 1.0)
        atk_a = self.attack.get(away, 1.0)
        dfn_a = self.defense.get(away, 1.0)

        hfa = 1.0 if neutral else self.home_adv

        mu_h = atk_h * dfn_a * hfa * self.base_rate
        mu_a = atk_a * dfn_h * self.base_rate

        ph = np.array([poisson.pmf(g, mu_h) for g in range(max_goals + 1)])
        pa = np.array([poisson.pmf(g, mu_a) for g in range(max_goals + 1)])

        matrix = np.outer(ph, pa)

        # Corrección Dixon-Coles para marcadores bajos
        for hg in range(min(2, max_goals + 1)):
            for ag in range(min(2, max_goals + 1)):
                matrix[hg, ag] *= self._tau(hg, ag, mu_h, mu_a, self.rho)

        # Renormalizar
        total = matrix.sum()
        if total > 0:
            matrix /= total

        return matrix

    def predict_outcomes(self, home: str, away: str, neutral: bool = False) -> dict:
        """Devuelve P(home win), P(draw), P(away win) desde la matriz."""
        matrix = self.predict_matrix(home, away, neutral=neutral)
        p_home = float(np.tril(matrix, -1).sum())
        p_draw = float(np.trace(matrix))
        p_away = float(np.triu(matrix, 1).sum())
        return {"home_win": p_home, "draw": p_draw, "away_win": p_away}

    def expected_goals(self, home: str, away: str, neutral: bool = False) -> dict:
        matrix = self.predict_matrix(home, away, neutral=neutral)
        goals_range = np.arange(matrix.shape[0])
        xg_h = float(np.sum(goals_range * matrix.sum(axis=1)))
        xg_a = float(np.sum(goals_range * matrix.sum(axis=0)))
        return {"home": round(xg_h, 3), "away": round(xg_a, 3)}

    @staticmethod
    def _tau(hg: int, ag: int, mu_h: float, mu_a: float, rho: float) -> float:
        """Factor de corrección Dixon-Coles para marcadores {0,1} × {0,1}."""
        if hg == 0 and ag == 0:
            return 1 - mu_h * mu_a * rho
        if hg == 1 and ag == 0:
            return 1 + mu_a * rho
        if hg == 0 and ag == 1:
            return 1 + mu_h * rho
        if hg == 1 and ag == 1:
            return 1 - rho
        return 1.0

    # ── Persistencia ──────────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        joblib.dump(self.__dict__, path)
        logger.info(f"Poisson model saved → {path}")

    @classmethod
    def load(cls, path: Path) -> "DixonColesPoisson":
        obj = cls()
        obj.__dict__.update(joblib.load(path))
        return obj
