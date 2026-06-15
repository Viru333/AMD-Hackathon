"""
Root Cause Predictor — reusable inference module.

Usage
-----
from ml.rootcause_predictor import RootCausePredictor
predictor = RootCausePredictor("models/rca_model.pkl",
                                "models/scaler_rca.pkl",
                                "models/rca_label_map.pkl")
result = predictor.predict({"cpu": 95, "memory": 88, "latency": 1200, "error_count": 230})
# {"root_cause": "Database Failure", "confidence": 0.91, "top3": [...]}
"""

import numpy as np
import pandas as pd
import joblib
import os
from typing import Any


class RootCausePredictor:
    """
    Wraps the trained XGBoost root-cause classifier with a clean inference API.

    Parameters
    ----------
    model_path  : path to rca_model.pkl
    scaler_path : path to scaler_rca.pkl
    label_path  : path to rca_label_map.pkl
    """

    NUMERIC_FEATURES = [
        "duration_min", "alert_volume", "error_count", "warn_count",
        "info_count", "cpu_util_peak", "memory_util_peak", "disk_util_peak",
        "latency_max_ms", "impacted_services",
    ]
    TOWERS = ["Compute", "Storage", "Network", "Database", "Cloud", "Application"]
    SERVICES = [
        "auth-service", "payment-gateway", "order-service", "inventory-api",
        "notification-service", "reporting-service", "analytics-engine",
        "cache-cluster", "message-broker", "api-gateway",
    ]

    def __init__(self, model_path: str, scaler_path: str, label_path: str):
        self.model      = joblib.load(model_path)
        self.scaler     = joblib.load(scaler_path)
        label_map       = joblib.load(label_path)
        self.inv_label_map = {v: k for k, v in label_map.items()}
        self.n_classes  = len(label_map)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Predict the most probable root cause.

        Returns
        -------
        {
            "root_cause" : "Database Failure",
            "confidence" : 0.91,
            "top3"       : [
                {"root_cause": "Database Failure", "confidence": 0.91},
                {"root_cause": "Network Failure",  "confidence": 0.06},
                {"root_cause": "Disk Failure",     "confidence": 0.02},
            ],
            "all_probabilities": {
                "Database Failure": 0.91,
                ...
            }
        }
        """
        X = self._build_feature_vector(features)
        X_scaled = self.scaler.transform(X)
        proba    = self.model.predict_proba(X_scaled)[0]
        pred_idx = int(np.argmax(proba))
        top3_idx = np.argsort(proba)[::-1][:3]

        return {
            "root_cause" : self.inv_label_map[pred_idx],
            "confidence" : round(float(proba[pred_idx]), 4),
            "top3"       : [
                {"root_cause": self.inv_label_map[int(i)], "confidence": round(float(proba[i]), 4)}
                for i in top3_idx
            ],
            "all_probabilities": {
                self.inv_label_map[i]: round(float(p), 4) for i, p in enumerate(proba)
            },
        }

    def predict_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Predict root causes for a list of feature dicts."""
        return [self.predict(r) for r in records]

    def explain(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Extended prediction with feature contribution hints based on
        the model's feature importances and input values.
        """
        result = self.predict(features)
        importances = dict(zip(
            self._feature_names(),
            self.model.feature_importances_,
        ))
        X = self._build_feature_vector(features).iloc[0].to_dict()

        # Weight importance by normalised input value (crude but helpful)
        contributions = {}
        numeric_vals  = {k: v for k, v in X.items() if not (k.startswith("tower_") or k.startswith("svc_"))}
        max_val       = max(abs(v) for v in numeric_vals.values()) or 1.0
        for feat, imp in importances.items():
            val = X.get(feat, 0.0)
            contributions[feat] = round(float(imp * abs(val) / max_val), 6)

        top5_contribs = sorted(contributions.items(), key=lambda x: -x[1])[:5]
        result["top5_contributing_features"] = [
            {"feature": k, "contribution": v} for k, v in top5_contribs
        ]
        return result

    # ------------------------------------------------------------------
    # Feature construction  (mirrors feature_engineering.py logic)
    # ------------------------------------------------------------------

    def _build_feature_vector(self, f: dict[str, Any]) -> pd.DataFrame:
        cpu      = float(f.get("cpu_util_peak",    f.get("cpu",     40.0)))
        memory   = float(f.get("memory_util_peak", f.get("memory",  50.0)))
        disk     = float(f.get("disk_util_peak",   f.get("disk",    50.0)))
        latency  = float(f.get("latency_max_ms",   f.get("latency", 200.0)))
        errors   = float(f.get("error_count",       5.0))
        warns    = float(f.get("warn_count",        20.0))
        infos    = float(f.get("info_count",        100.0))
        duration = float(f.get("duration_min",      30.0))
        alert_vol= float(f.get("alert_volume",      3.0))
        impacted = float(f.get("impacted_services", 1.0))
        tower    = str(f.get("tower",   "Application"))
        service  = str(f.get("service", "api-gateway"))

        error_warn_ratio = errors / (warns + 1)
        alert_per_hour   = alert_vol / (duration / 60 + 0.01)
        composite_load   = cpu * 0.4 + memory * 0.3 + disk * 0.3
        log_error_count  = np.log1p(errors)
        log_latency      = np.log1p(latency)

        row = {
            "duration_min":     duration,
            "alert_volume":     alert_vol,
            "error_count":      errors,
            "warn_count":       warns,
            "info_count":       infos,
            "cpu_util_peak":    cpu,
            "memory_util_peak": memory,
            "disk_util_peak":   disk,
            "latency_max_ms":   latency,
            "impacted_services":impacted,
            "error_warn_ratio": error_warn_ratio,
            "alert_per_hour":   alert_per_hour,
            "composite_load":   composite_load,
            "log_error_count":  log_error_count,
            "log_latency":      log_latency,
        }
        for t in self.TOWERS:
            row[f"tower_{t}"] = int(tower == t)
        for s in self.SERVICES:
            row[f"svc_{s}"] = int(service == s)

        return pd.DataFrame([row])

    def _feature_names(self) -> list[str]:
        base = list(self._build_feature_vector({}).columns)
        return base


# ------------------------------------------------------------------
# FastAPI schema helpers
# ------------------------------------------------------------------

def rca_input_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "cpu":              {"type": "number"},
            "memory":           {"type": "number"},
            "disk":             {"type": "number"},
            "latency":          {"type": "number"},
            "error_count":      {"type": "integer"},
            "warn_count":       {"type": "integer"},
            "alert_volume":     {"type": "integer"},
            "duration_min":     {"type": "number"},
            "impacted_services":{"type": "integer"},
            "tower":            {"type": "string"},
            "service":          {"type": "string"},
        },
        "required": ["cpu", "memory", "latency", "error_count"],
    }


def rca_output_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "root_cause":  {"type": "string"},
            "confidence":  {"type": "number"},
            "top3":        {"type": "array",  "items": {"type": "object"}},
            "all_probabilities": {"type": "object"},
        },
    }


# ------------------------------------------------------------------
# CLI smoke test
# ------------------------------------------------------------------
if __name__ == "__main__":
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    predictor = RootCausePredictor(
        model_path  = os.path.join(BASE, "models", "rca_model.pkl"),
        scaler_path = os.path.join(BASE, "models", "scaler_rca.pkl"),
        label_path  = os.path.join(BASE, "models", "rca_label_map.pkl"),
    )

    test_cases = [
        {"cpu": 15,  "memory": 20,  "disk": 25,  "latency": 12000, "error_count": 800,  "tower": "Database"},
        {"cpu": 10,  "memory": 15,  "disk": 30,  "latency": 25000, "error_count": 200,  "tower": "Network"},
        {"cpu": 30,  "memory": 92,  "disk": 40,  "latency": 400,   "error_count": 50,   "tower": "Application"},
        {"cpu": 98,  "memory": 60,  "disk": 55,  "latency": 600,   "error_count": 30,   "tower": "Compute"},
        {"cpu": 25,  "memory": 30,  "disk": 95,  "latency": 300,   "error_count": 100,  "tower": "Storage"},
        {"cpu": 5,   "memory": 8,   "disk": 10,  "latency": 200,   "error_count": 500,  "tower": "Cloud"},
        {"cpu": 95,  "memory": 90,  "disk": 88,  "latency": 1500,  "error_count": 300,  "tower": "Cloud"},
        {"cpu": 20,  "memory": 25,  "disk": 30,  "latency": 500,   "error_count": 1000, "tower": "Application"},
    ]

    print("\nRoot Cause Predictor — smoke test")
    print("=" * 70)
    for tc in test_cases:
        result = predictor.predict(tc)
        print(f"  Tower={tc.get('tower','?'):12s} → {result['root_cause']:30s} ({result['confidence']:.3f})")
        for r in result["top3"][1:]:
            print(f"      2nd/3rd: {r['root_cause']:30s} ({r['confidence']:.3f})")
        print()
