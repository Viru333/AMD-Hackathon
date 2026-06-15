"""
ML inference layer — loads the three trained models once at startup
and exposes clean predict_*() functions.
"""
from __future__ import annotations
import logging
from typing import Any

import numpy as np
import joblib

from backend.config import (
    SEVERITY_MODEL_PATH, ANOMALY_MODEL_PATH, RCA_MODEL_PATH,
    SCALER_SEVERITY_PATH, SCALER_ANOMALY_PATH, SCALER_RCA_PATH,
    SEV_LABEL_MAP_PATH, RCA_LABEL_MAP_PATH, ANOMALY_SCORE_PATH,
)
from backend.ml.preprocessing import (
    build_severity_features, build_anomaly_features, build_rca_features,
)

logger = logging.getLogger(__name__)


class MLModels:
    """Singleton model registry — call `load()` once at startup."""

    _instance: "MLModels | None" = None

    def __init__(self):
        self.severity_model  = None
        self.anomaly_model   = None
        self.rca_model       = None
        self.scaler_sev      = None
        self.scaler_anom     = None
        self.scaler_rca      = None
        self.sev_label_map:  dict[str, int] = {}
        self.rca_label_map:  dict[str, int] = {}
        self.inv_sev_map:    dict[int, str] = {}
        self.inv_rca_map:    dict[int, str] = {}
        self.anom_score_min: float = 0.0
        self.anom_score_max: float = 1.0
        self._loaded = False

    @classmethod
    def get(cls) -> "MLModels":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self) -> None:
        if self._loaded:
            return

        logger.info("Loading ML models …")
        try:
            self.severity_model = joblib.load(SEVERITY_MODEL_PATH)
            self.scaler_sev     = joblib.load(SCALER_SEVERITY_PATH)
            self.sev_label_map  = joblib.load(SEV_LABEL_MAP_PATH)
            self.inv_sev_map    = {v: k for k, v in self.sev_label_map.items()}
            logger.info("  Severity model loaded")
        except Exception as e:
            logger.warning(f"  Severity model unavailable: {e}")

        try:
            self.anomaly_model  = joblib.load(ANOMALY_MODEL_PATH)
            self.scaler_anom    = joblib.load(SCALER_ANOMALY_PATH)
            params              = joblib.load(ANOMALY_SCORE_PATH)
            self.anom_score_min = params["score_min"]
            self.anom_score_max = params["score_max"]
            logger.info("  Anomaly model loaded")
        except Exception as e:
            logger.warning(f"  Anomaly model unavailable: {e}")

        try:
            self.rca_model     = joblib.load(RCA_MODEL_PATH)
            self.scaler_rca    = joblib.load(SCALER_RCA_PATH)
            self.rca_label_map = joblib.load(RCA_LABEL_MAP_PATH)
            self.inv_rca_map   = {v: k for k, v in self.rca_label_map.items()}
            logger.info("  RCA model loaded")
        except Exception as e:
            logger.warning(f"  ⚠️  RCA model unavailable: {e}")

        self._loaded = True
        logger.info("ML model loading complete.")

    # ─────────────────────────────────────────────────────────────
    # Public inference functions
    # ─────────────────────────────────────────────────────────────

    def predict_severity(self, features: dict[str, Any]) -> dict[str, Any]:
        if self.severity_model is None:
            return {"severity": "P2 High", "confidence": 0.5, "all_probabilities": {}}

        X = build_severity_features(features)
        X_scaled = self.scaler_sev.transform(X)
        proba    = self.severity_model.predict_proba(X_scaled)[0]
        pred_idx = int(np.argmax(proba))
        label    = self.inv_sev_map.get(pred_idx, "P2 High")
        all_prob = {
            self.inv_sev_map[i]: round(float(p), 4)
            for i, p in enumerate(proba)
            if i in self.inv_sev_map
        }
        return {
            "severity":         label,
            "confidence":       round(float(proba[pred_idx]), 4),
            "all_probabilities": all_prob,
        }

    def detect_anomaly(self, features: dict[str, Any]) -> dict[str, Any]:
        if self.anomaly_model is None:
            return {"anomaly": False, "score": 0.0, "threshold": 0.5, "raw_score": 0.0}

        X = build_anomaly_features(features)
        X_scaled  = self.scaler_anom.transform(X)
        raw       = float(self.anomaly_model.decision_function(X_scaled)[0])
        score     = -raw
        score_norm = (score - self.anom_score_min) / (self.anom_score_max - self.anom_score_min + 1e-9)
        score_norm = float(np.clip(score_norm, 0.0, 1.0))
        is_anomaly = bool(self.anomaly_model.predict(X_scaled)[0] == -1)
        return {
            "anomaly":   is_anomaly,
            "score":     round(score_norm, 4),
            "threshold": 0.5,
            "raw_score": round(raw, 6),
        }

    def predict_root_cause(self, features: dict[str, Any]) -> dict[str, Any]:
        if self.rca_model is None:
            return {
                "root_cause": "Database Failure", "confidence": 0.5,
                "top3": [], "all_probabilities": {},
            }

        X = build_rca_features(features)
        X_scaled = self.scaler_rca.transform(X)
        proba    = self.rca_model.predict_proba(X_scaled)[0]
        pred_idx = int(np.argmax(proba))
        top3_idx = np.argsort(proba)[::-1][:3]
        label    = self.inv_rca_map.get(pred_idx, "Unknown")
        return {
            "root_cause": label,
            "confidence": round(float(proba[pred_idx]), 4),
            "top3": [
                {"root_cause": self.inv_rca_map.get(int(i), "?"),
                 "confidence": round(float(proba[i]), 4)}
                for i in top3_idx
            ],
            "all_probabilities": {
                self.inv_rca_map[i]: round(float(p), 4)
                for i, p in enumerate(proba)
                if i in self.inv_rca_map
            },
        }


# ── Module-level helpers (for use in nodes / routes) ─────────────

def get_models() -> MLModels:
    return MLModels.get()
