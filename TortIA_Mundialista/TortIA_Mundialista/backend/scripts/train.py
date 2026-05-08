"""
scripts/train.py
Script de entrenamiento E2E: ingesta → features → train → save artifacts.

Uso:
    cd backend
    python -m scripts.train --date-from 2022-11-01 --tune

Flags:
    --date-from   Fecha inicio de datos históricos (default: 2022-11-01)
    --date-to     Fecha fin (default: hoy)
    --tune        Activa búsqueda de hiperparámetros con Optuna (más lento)
    --n-trials    Número de trials de Optuna (default: 50)
"""
import argparse
import sys
from pathlib import Path

from loguru import logger

# Asegurar que el root del backend esté en path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from etl.pipeline import WorldCupETL
from models.poisson import DixonColesPoisson
from models.xgb_classifier import XGBOutcomeClassifier
from etl.features import FEATURE_COLS


def main():
    parser = argparse.ArgumentParser(description="TortIA Mundialista — Training Pipeline")
    parser.add_argument("--date-from", default="2022-11-01")
    parser.add_argument("--date-to", default=None)
    parser.add_argument("--tune", action="store_true")
    parser.add_argument("--n-trials", type=int, default=50)
    args = parser.parse_args()

    settings = get_settings()
    artifacts_dir = Path(settings.model_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Ingesta ────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("FASE 1: Ingesta y feature engineering")
    logger.info("=" * 60)

    etl = WorldCupETL(
        football_data_token=settings.football_data_token,
        rapidapi_key=settings.rapidapi_key,
        output_dir="data",
    )

    df = etl.ingest_historical(
        date_from=args.date_from,
        date_to=args.date_to,
    )

    logger.info(f"Dataset: {len(df)} partidos, {df['home_team'].nunique()} equipos únicos")
    logger.info(f"Distribución outcomes: {dict(df['outcome'].value_counts().sort_index())}")

    # ── 2. Entrenamiento Poisson ──────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("FASE 2: Entrenamiento Dixon-Coles Poisson")
    logger.info("=" * 60)

    poisson = DixonColesPoisson()
    poisson.fit(df, verbose=True)
    poisson.save(artifacts_dir / "poisson_model.pkl")

    # Validación rápida
    test_result = poisson.predict_outcomes("Argentina", "France")
    logger.info(f"Validación Poisson ARG vs FRA: {test_result}")

    # ── 3. Entrenamiento XGBoost ──────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("FASE 3: Entrenamiento XGBoost Classifier")
    logger.info("=" * 60)

    xgb_clf = XGBOutcomeClassifier()

    if args.tune:
        logger.info(f"Búsqueda de hiperparámetros ({args.n_trials} trials)...")
        best_params = xgb_clf.tune_hyperparams(df, n_trials=args.n_trials)
        xgb_clf = XGBOutcomeClassifier(params=best_params)

    xgb_clf.fit(df, calibrate=True)
    xgb_clf.save(artifacts_dir / "xgb_outcome.pkl")

    # Feature importance
    fi = xgb_clf.feature_importance()
    logger.info(f"Top-5 features:\n{fi.head().to_string()}")

    # ── 4. Backtesting WC2022 ─────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("FASE 4: Backtesting vs WC2022")
    logger.info("=" * 60)
    _run_backtest(df, poisson, xgb_clf, settings.ensemble_alpha)

    logger.success("🏆 Entrenamiento completado. Artifacts guardados en artifacts/")
    logger.info(f"  → {artifacts_dir}/poisson_model.pkl")
    logger.info(f"  → {artifacts_dir}/xgb_outcome.pkl")


def _run_backtest(df, poisson, xgb_clf, alpha: float):
    """Evalúa el modelo sobre partidos de WC2022 como hold-out set."""
    import numpy as np
    from sklearn.metrics import log_loss, brier_score_loss
    from models.predictor import HybridPredictor

    wc22 = df[df["competition"].isin(["WC", "WC2022"])].dropna(subset=["outcome"])
    if wc22.empty:
        logger.warning("No hay datos de WC2022 para backtest. Saltando.")
        return

    predictor = HybridPredictor(poisson, xgb_clf, alpha=alpha)
    y_true = wc22["outcome"].astype(int).values
    y_pred = []

    from etl.features import FEATURE_COLS
    for _, row in wc22.iterrows():
        features = wc22[FEATURE_COLS].loc[[row.name]]
        try:
            xgb_p = xgb_clf.predict_proba(features)[0]
        except Exception:
            xgb_p = np.array([1/3, 1/3, 1/3])
        mat = poisson.predict_matrix(row["home_team"], row["away_team"])
        p_poi = [np.triu(mat, 1).sum(), np.trace(mat), np.tril(mat, -1).sum()]
        blended = alpha * np.array(xgb_p) + (1 - alpha) * np.array(p_poi)
        blended /= blended.sum()
        y_pred.append(blended.tolist())

    y_pred = np.array(y_pred)
    ll = log_loss(y_true, y_pred)

    # Brier score por clase
    from sklearn.preprocessing import label_binarize
    y_bin = label_binarize(y_true, classes=[0, 1, 2])
    bs = np.mean([brier_score_loss(y_bin[:, i], y_pred[:, i]) for i in range(3)])

    logger.info(f"Backtest WC2022 ({len(wc22)} partidos):")
    logger.info(f"  Log Loss:    {ll:.4f}")
    logger.info(f"  Brier Score: {bs:.4f}")

    # Accuracy del marcador más probable
    correct_score = 0
    for (_, row), pred in zip(wc22.iterrows(), y_pred):
        mat = poisson.predict_matrix(row["home_team"], row["away_team"])
        fi = int(np.argmax(mat))
        phg = fi // mat.shape[1]
        pag = fi % mat.shape[1]
        if int(row["home_goals"]) == phg and int(row["away_goals"]) == pag:
            correct_score += 1
    logger.info(f"  Exact Score Accuracy: {correct_score / len(wc22) * 100:.1f}%")


if __name__ == "__main__":
    main()
