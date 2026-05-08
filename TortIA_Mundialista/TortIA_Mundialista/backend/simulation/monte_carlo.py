"""
simulation/monte_carlo.py
Simulación Monte Carlo del torneo completo (10k iteraciones).
Soporta el formato WC2026: 48 equipos, 12 grupos de 4, R32 → Final.
"""
from __future__ import annotations

import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger
from tqdm import tqdm

from models.predictor import HybridPredictor

# ── Grupos WC2026 (placeholder — actualizar con sorteo oficial) ───────────────
WC2026_GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "Poland", "Saudi Arabia", "Ecuador"],
    "B": ["USA", "England", "Iran", "Wales"],
    "C": ["Argentina", "Mexico", "Poland", "Saudi Arabia"],  # placeholder
    "D": ["France", "Australia", "Tunisia", "Denmark"],
    "E": ["Spain", "Costa Rica", "Germany", "Japan"],
    "F": ["Belgium", "Canada", "Morocco", "Croatia"],
    "G": ["Brazil", "Serbia", "Switzerland", "Cameroon"],
    "H": ["Portugal", "Ghana", "Uruguay", "South Korea"],
    "I": ["Netherlands", "Senegal", "Qatar", "Ecuador"],
    "J": ["Colombia", "Panama", "Peru", "Canada"],
    "K": ["Chile", "Bolivia", "Paraguay", "Venezuela"],
    "L": ["New Zealand", "Australia", "Indonesia", "Uzbekistan"],
}


def _sample_match(
    home: str,
    away: str,
    predictor: HybridPredictor,
    features: pd.DataFrame,
    neutral: bool = True,
) -> tuple[int, int]:
    """Samplea UN resultado desde la distribución de Poisson."""
    matrix = predictor.poisson.predict_matrix(home, away, neutral=neutral)
    flat = matrix.flatten()
    # Corrección numérica: asegurar que sea distribución válida
    flat = np.clip(flat, 0, None)
    flat /= flat.sum()
    idx = np.random.choice(len(flat), p=flat)
    hg = idx // matrix.shape[1]
    ag = idx % matrix.shape[1]
    return int(hg), int(ag)


def _simulate_group(
    teams: list[str],
    predictor: HybridPredictor,
    default_features: pd.DataFrame,
) -> list[str]:
    """Simula fase de grupos. Devuelve equipos ordenados por posición final."""
    standings: dict[str, dict] = {
        t: {"pts": 0, "gd": 0, "gf": 0} for t in teams
    }

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            home, away = teams[i], teams[j]
            hg, ag = _sample_match(home, away, predictor, default_features)

            if hg > ag:
                standings[home]["pts"] += 3
            elif hg == ag:
                standings[home]["pts"] += 1
                standings[away]["pts"] += 1
            else:
                standings[away]["pts"] += 3

            standings[home]["gd"] += hg - ag
            standings[away]["gd"] += ag - hg
            standings[home]["gf"] += hg
            standings[away]["gf"] += ag

    return sorted(
        teams,
        key=lambda t: (
            standings[t]["pts"],
            standings[t]["gd"],
            standings[t]["gf"],
            random.random(),  # desempate aleatorio
        ),
        reverse=True,
    )


def _simulate_knockout_match(
    home: str,
    away: str,
    predictor: HybridPredictor,
    default_features: pd.DataFrame,
    elo_home: float = 1500.0,
    elo_away: float = 1500.0,
) -> str:
    """
    Simula partido de eliminatoria.
    Si hay empate en 90' → prórroga → penales.
    """
    hg, ag = _sample_match(home, away, predictor, default_features, neutral=True)

    if hg != ag:
        return home if hg > ag else away

    # Prórroga (tasa goles reducida ~30%)
    et_hg = np.random.poisson(0.25)
    et_ag = np.random.poisson(0.25)
    if et_hg != et_ag:
        return home if et_hg > et_ag else away

    # Penales: sesgo Elo pequeño
    elo_diff = elo_home - elo_away
    p_home_pen = 0.5 + 0.02 * np.tanh(elo_diff / 400)
    return home if np.random.random() < p_home_pen else away


def _run_bracket(
    teams: list[str],
    predictor: HybridPredictor,
    default_features: pd.DataFrame,
) -> dict[str, str]:
    """
    Corre el bracket eliminatorio desde R32 hasta la Final.
    Devuelve dict con resultados por ronda.
    """
    rounds = {
        "R32": teams,
        "R16": [],
        "QF": [],
        "SF": [],
        "Final": [],
        "Champion": "",
    }

    current = teams.copy()
    round_names = ["R16", "QF", "SF", "Final"]

    for round_name in round_names:
        winners = []
        for i in range(0, len(current), 2):
            if i + 1 >= len(current):
                winners.append(current[i])
                continue
            winner = _simulate_knockout_match(
                current[i], current[i + 1], predictor, default_features
            )
            winners.append(winner)
        rounds[round_name] = winners
        current = winners

    rounds["Champion"] = current[0] if current else ""
    return rounds


def _single_simulation(args: tuple) -> dict:
    """Una simulación completa del torneo. Ejecutada en proceso separado."""
    groups, predictor, default_features, seed = args
    np.random.seed(seed)
    random.seed(seed)

    group_names = list(groups.keys())
    group_results: dict[str, list[str]] = {}

    for gname, teams in groups.items():
        ranked = _simulate_group(teams, predictor, default_features)
        group_results[gname] = ranked

    # Armado de R32 (cruces estilo WC: 1A vs 2B, 1C vs 2D, etc.)
    r32: list[str] = []
    for i in range(0, len(group_names), 2):
        g1, g2 = group_names[i], group_names[i + 1]
        r1, r2 = group_results[g1], group_results[g2]
        r32.extend([r1[0], r2[1], r2[0], r1[1]])  # 1° cruza con 2° del otro grupo

    bracket = _run_bracket(r32, predictor, default_features)

    # Registrar participación por equipo en cada ronda
    result: dict[str, dict] = {}
    for team in [t for teams in groups.values() for t in teams]:
        result[team] = {
            "champion": int(bracket["Champion"] == team),
            "final": int(team in bracket.get("Final", [])),
            "sf": int(team in bracket.get("SF", [])),
            "qf": int(team in bracket.get("QF", [])),
            "r16": int(team in bracket.get("R16", [])),
            "group_exit": int(team not in bracket.get("R16", []) + bracket.get("QF", []) + bracket.get("SF", []) + bracket.get("Final", [])),
        }
    return result


def run_tournament_simulation(
    groups: dict[str, list[str]],
    predictor: HybridPredictor,
    default_features: pd.DataFrame,
    n_simulations: int = 10_000,
    n_workers: int = 4,
) -> pd.DataFrame:
    """
    Ejecuta N simulaciones Monte Carlo del torneo.

    Returns:
        DataFrame con columnas: team, win_pct, final_pct, sf_pct, qf_pct, r16_pct.
    """
    logger.info(f"Iniciando {n_simulations:,} simulaciones con {n_workers} workers...")

    args = [
        (groups, predictor, default_features, seed)
        for seed in range(n_simulations)
    ]

    all_results: list[dict] = []

    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        futures = [pool.submit(_single_simulation, a) for a in args]
        for future in tqdm(as_completed(futures), total=n_simulations, desc="Simulando"):
            try:
                all_results.append(future.result())
            except Exception as e:
                logger.error(f"Simulation error: {e}")

    # Agregar resultados
    all_teams = sorted({t for r in all_results for t in r.keys()})
    rows = []
    for team in all_teams:
        counts = {k: sum(r.get(team, {}).get(k, 0) for r in all_results) for k in
                  ["champion", "final", "sf", "qf", "r16"]}
        n = len(all_results)
        rows.append({
            "team": team,
            "win_pct": round(counts["champion"] / n * 100, 2),
            "final_pct": round(counts["final"] / n * 100, 2),
            "sf_pct": round(counts["sf"] / n * 100, 2),
            "qf_pct": round(counts["qf"] / n * 100, 2),
            "r16_pct": round(counts["r16"] / n * 100, 2),
        })

    df = pd.DataFrame(rows).sort_values("win_pct", ascending=False).reset_index(drop=True)
    logger.success(f"Simulación completada. Campeón más probable: {df.iloc[0]['team']} ({df.iloc[0]['win_pct']}%)")
    return df
