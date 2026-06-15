"""
Severity Predictor — reusable inference module.

Usage
-----
from ml.severity_predictor import SeverityPredictor
predictor = SeverityPredictor("models/severity_model.pkl",
                               "models/scaler_severity.pkl",
                               "models/severity_label_map.pkl")
result = predictor.predict({"cpu": 95, "memory": 88, "latency": 1200, "error_count": 230})
# {"severity": "P1 Critical", "confidence": 0.93, "all_probabilities": {...}}
"""

import numpy as np
import pandas as pd
import joblib
import os
from typing import Any


class SeverityPredictor:
    """
    Wraps the trained XGBoost severity classifier with a clean inference API.

    Parameters
    ----------
    model_path  : path to severity_model.pkl
    scaler_path : path to scaler_severity.pkl
    label_path  : path to severity_label_map.pkl
    """

    # Canonical feature order expected by the model
    NUMERIC_FEATURES = [
        "duration_min", "alert_volume", "error_count", "warn_count",
        "info_count", "cpu_util_peak", "memory_util_peak", "disk_util_peak",
        "latency_max_ms", "impacted_services",
    ]
    DERIVED_FEATURES = [
        "error_warn_ratio", "alert_per_hour", "composite_load",
        "log_error_count", "log_latency",
    ]
    TOWERS   = ["Compute", "Storage", "Network", "Database", "Cloud", "Application"]
    SERVICES = [
        "auth-service", "payment-gateway", "order-service", "inventory-api",
        "notification-service", "reporting-service", "analytics-engine",
        "cache-cluster", "message-broker", "api-gateway",
    ]

    def __init__(self, model_path: str, scaler_path: str, label_path: str):
        self.model  = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        label_map   = joblib.load(label_path)
        self.inv_label_map = {v: k for k, v in label_map.items()}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Predict severity from a raw feature dict.

        Minimum required keys
        ---------------------
        cpu_util_peak, memory_util_peak, disk_util_peak,
        latency_max_ms, error_count

        All others default to sensible values if omitted.

        Returns
        -------
        {
            "severity"         : "P1 Critical",
            "confidence"       : 0.93,
            "all_probabilities": {"P1 Critical": 0.93, "P2 High": 0.05, ...}
        }
        """
        X = self._build_feature_vector(features)
        X_scaled = self.scaler.transform(X)
        proba    = self.model.predict_proba(X_scaled)[0]
        pred_idx = int(np.argmax(proba))
        label    = self.inv_label_map[pred_idx]
        all_prob = {self.inv_label_map[i]: round(float(p), 4) for i, p in enumerate(proba)}
        return {
            "severity"         : label,
            "confidence"       : round(float(proba[pred_idx]), 4),
            "all_probabilities": all_prob,
        }

    def predict_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Predict severity for a list of feature dicts."""
        return [self.predict(r) for r in records]

    # ------------------------------------------------------------------
    # Feature construction
    # ------------------------------------------------------------------

    def _build_feature_vector(self, f: dict[str, Any]) -> pd.DataFrame:
        cpu      = float(f.get("cpu_util_peak",    f.get("cpu",    40.0)))
        memory   = float(f.get("memory_util_peak", f.get("memory", 50.0)))
        disk     = float(f.get("disk_util_peak",   f.get("disk",   50.0)))
        latency  = float(f.get("latency_max_ms",   f.get("latency", 200.0)))
        errors   = float(f.get("error_count",      f.get("error_count", 5.0)))
        warns    = float(f.get("warn_count",       20.0))
        infos    = float(f.get("info_count",       100.0))
        duration = float(f.get("duration_min",     30.0))
        alert_vol= float(f.get("alert_volume",     3.0))
        impacted = float(f.get("impacted_services",1.0))
        tower    = str(f.get("tower",    "Application"))
        service  = str(f.get("service",  "api-gateway"))

        # Derived
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

        # Tower one-hot
        for t in self.TOWERS:
            row[f"tower_{t}"] = int(tower == t)

        # Service one-hot
        for s in self.SERVICES:
            row[f"svc_{s}"] = int(service == s)

        return pd.DataFrame([row])


# ------------------------------------------------------------------
# FastAPI-compatible schema helpers  (pydantic-free, plain dicts)
# ------------------------------------------------------------------

def severity_input_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "cpu":         {"type": "number", "description": "CPU utilisation % (0-100)"},
            "memory":      {"type": "number", "description": "Memory utilisation % (0-100)"},
            "disk":        {"type": "number", "description": "Disk utilisation % (0-100)"},
            "latency":     {"type": "number", "description": "Max latency in ms"},
            "error_count": {"type": "integer","description": "Error log count"},
            "warn_count":  {"type": "integer","description": "Warning log count"},
            "alert_volume":{"type": "integer","description": "Number of alerts fired"},
            "duration_min":{"type": "number", "description": "Incident duration (min)"},
            "tower":       {"type": "string", "description": "Infrastructure tower"},
            "service":     {"type": "string", "description": "Affected service name"},
        },
        "required": ["cpu", "memory", "latency", "error_count"],
    }


def severity_output_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "severity":         {"type": "string", "enum": ["P1 Critical","P2 High","P3 Medium","P4 Low"]},
            "confidence":       {"type": "number"},
            "all_probabilities":{"type": "object"},
        },
    }


# ------------------------------------------------------------------
# CLI smoke test
# ------------------------------------------------------------------
if __name__ == "__main__":
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    predictor = SeverityPredictor(
        model_path  = os.path.join(BASE, "models", "severity_model.pkl"),
        scaler_path = os.path.join(BASE, "models", "scaler_severity.pkl"),
        label_path  = os.path.join(BASE, "models", "severity_label_map.pkl"),
    )

    test_cases = [
        {"cpu": 95, "memory": 88, "latency": 5000, "error_count": 500},   # expect P1
        {"cpu": 70, "memory": 65, "latency": 800,  "error_count": 50},    # expect P2
        {"cpu": 40, "memory": 50, "latency": 300,  "error_count": 10},    # expect P3/P4
        {"cpu": 15, "memory": 20, "latency": 80,   "error_count": 1},     # expect P4
    ]
    print("\nSeverity Predictor — smoke test")
    print("=" * 45)
    for tc in test_cases:
        result = predictor.predict(tc)
        print(f"  {tc}  →  {result['severity']}  ({result['confidence']:.3f})")
