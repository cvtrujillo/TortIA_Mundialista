"""
models/xgb_classifier.py
Clasificador XGBoost 3-clases (0=away win, 1=draw, 2=home win).
Incluye calibración isotónica y búsqueda de hiperparámetros con Optuna.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from loguru import logger
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder

from etl.features import FEATURE_COLS


class XGBOutcomeClassifier:
    """
    Gradient boosted classifier entrenado sobre features de partido.
    Salida: [P(away win), P(draw), P(home win)] calibradas con isotonic.
    """

    DEFAULT_PARAMS = {
        "n_estimators": 500,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "gamma": 0.1,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "objective": "multi:softprob",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "use_label_encoder": False,
        "random_state": 42,
        "n_jobs": -1,
    }

    def __init__(self, params: Optional[dict] = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self.model: Optional[xgb.XGBClassifier] = None
        self.calibrated: Optional[CalibratedClassifierCV] = None
        self.feature_cols = FEATURE_COLS
        self.is_fitted: bool = False

    def fit(
        self,
        df: pd.DataFrame,
        calibrate: bool = True,
        early_stopping_rounds: int = 50,
    ) -> "XGBOutcomeClassifier":
        """Entrena el clasificador sobre el DataFrame con features calculadas."""
        df_train = df.dropna(subset=["outcome"] + self.feature_cols).copy()
        X = df_train[self.feature_cols].astype(float)
        y = df_train["outcome"].astype(int)

        logger.info(
            f"Training XGB: {len(df_train)} samples, "
            f"classes={dict(y.value_counts().sort_index())}"
        )

        # Train/val split temporal (no shuffle para evitar leakage)
        split_idx = int(len(X) * 0.85)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

        self.model = xgb.XGBClassifier(**self.params)
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
            early_stopping_rounds=early_stopping_rounds,
        )

        best_round = self.model.best_iteration
        logger.info(f"Best round: {best_round}, val_mlogloss={self.model.best_score:.4f}")

        if calibrate:
            logger.info("Calibrating probabilities with isotonic regression...")
            # Re-entrena sobre todo para calibración
            base_clf = xgb.XGBClassifier(**{**self.params, "n_estimators": best_round})
            self.calibrated = CalibratedClassifierCV(
                base_clf, method="isotonic", cv=StratifiedKFold(3)
            )
            self.calibrated.fit(X, y)

        self.is_fitted = True
        logger.success("XGBOutcomeClassifier fitted.")
        return self

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        """
        Devuelve array (n, 3): [P(away), P(draw), P(home)] calibrados.
        """
        if not self.is_fitted:
            raise RuntimeError("Modelo no ajustado.")

        X = features[self.feature_cols].astype(float)
        clf = self.calibrated if self.calibrated is not None else self.model
        return clf.predict_proba(X)

    def feature_importance(self) -> pd.DataFrame:
        """SHAP-style importances de features (gain)."""
        if self.model is None:
            return pd.DataFrame()
        imp = self.model.get_booster().get_score(importance_type="gain")
        df = pd.DataFrame(list(imp.items()), columns=["feature", "gain"])
        df["gain_pct"] = df["gain"] / df["gain"].sum() * 100
        return df.sort_values("gain_pct", ascending=False)

    def tune_hyperparams(self, df: pd.DataFrame, n_trials: int = 50) -> dict:
        """
        Búsqueda de hiperparámetros con Optuna.
        Devuelve los mejores params para pasar a __init__.
        """
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        df_fit = df.dropna(subset=["outcome"] + self.feature_cols)
        X = df_fit[self.feature_cols].astype(float).values
        y = df_fit["outcome"].astype(int).values

        def objective(trial: optuna.Trial) -> float:
            from sklearn.metrics import log_loss
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 200, 800),
                "max_depth": trial.suggest_int("max_depth", 3, 7),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "gamma": trial.suggest_float("gamma", 0, 0.5),
                "reg_alpha": trial.suggest_float("reg_alpha", 0, 1.0),
                "objective": "multi:softprob",
                "num_class": 3,
                "eval_metric": "mlogloss",
                "use_label_encoder": False,
                "random_state": 42,
            }
            cv = StratifiedKFold(n_splits=4, shuffle=False)
            losses = []
            for tr_idx, val_idx in cv.split(X, y):
                clf = xgb.XGBClassifier(**params)
                clf.fit(X[tr_idx], y[tr_idx], verbose=False)
                proba = clf.predict_proba(X[val_idx])
                losses.append(log_loss(y[val_idx], proba))
            return float(np.mean(losses))

        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        logger.success(f"Best params: {study.best_params} (loss={study.best_value:.4f})")
        return study.best_params

    # ── Persistencia ──────────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        joblib.dump({
            "model": self.model,
            "calibrated": self.calibrated,
            "feature_cols": self.feature_cols,
            "is_fitted": self.is_fitted,
        }, path)
        logger.info(f"XGB model saved → {path}")

    @classmethod
    def load(cls, path: Path) -> "XGBOutcomeClassifier":
        data = joblib.load(path)
        obj = cls()
        obj.model = data["model"]
        obj.calibrated = data["calibrated"]
        obj.feature_cols = data["feature_cols"]
        obj.is_fitted = data["is_fitted"]
        return obj
