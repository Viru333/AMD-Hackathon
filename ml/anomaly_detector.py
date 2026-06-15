"""
Anomaly Predictor — reusable inference module.

Usage
-----
from ml.anomaly_predictor import AnomalyPredictor
predictor = AnomalyPredictor("models/anomaly_model.pkl",
                              "models/scaler_anomaly.pkl",
                              "models/anomaly_score_params.pkl")
result = predictor.detect({"cpu": 95, "memory": 88, "latency": 1200, "error_rate": 12.5})
# {"anomaly": True, "score": 0.87, "threshold": 0.5}
"""

import numpy as np
import pandas as pd
import joblib
import os
from typing import Any


class AnomalyPredictor:
    """
    Wraps the trained Isolation Forest with a clean inference API.

    Parameters
    ----------
    model_path       : path to anomaly_model.pkl
    scaler_path      : path to scaler_anomaly.pkl
    score_params_path: path to anomaly_score_params.pkl
    threshold        : normalised anomaly score threshold (default 0.5)
    """

    NUMERIC_FEATURES = [
        "cpu_util", "memory_util", "disk_util",
        "net_in_mbps", "net_out_mbps",
        "latency_ms", "error_rate",
        "request_rate", "gc_pause_ms", "thread_count",
    ]
    ROLL_SOURCES = ["cpu_util", "memory_util", "latency_ms", "error_rate"]
    TOWERS = ["Compute", "Storage", "Network", "Database", "Cloud", "Application"]

    def __init__(
        self,
        model_path: str,
        scaler_path: str,
        score_params_path: str,
        threshold: float = 0.5,
    ):
        self.model       = joblib.load(model_path)
        self.scaler      = joblib.load(scaler_path)
        score_params     = joblib.load(score_params_path)
        self.score_min   = score_params["score_min"]
        self.score_max   = score_params["score_max"]
        self.threshold   = threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Detect anomaly from a raw metrics dict.

        Minimum required keys
        ---------------------
        cpu_util (or cpu), memory_util (or memory),
        latency_ms (or latency), error_rate

        Returns
        -------
        {
            "anomaly"   : True,
            "score"     : 0.87,       # normalised [0, 1]; higher = more anomalous
            "threshold" : 0.5,
            "raw_score" : -0.12       # decision_function output (negative = anomaly)
        }
        """
        X = self._build_feature_vector(features)
        X_scaled  = self.scaler.transform(X)

        raw       = float(self.model.decision_function(X_scaled)[0])
        score     = -raw                                               # positive = anomalous
        score_norm = (score - self.score_min) / (self.score_max - self.score_min + 1e-9)
        score_norm = float(np.clip(score_norm, 0.0, 1.0))
        is_anomaly = bool(self.model.predict(X_scaled)[0] == -1)

        return {
            "anomaly"   : is_anomaly,
            "score"     : round(score_norm, 4),
            "threshold" : self.threshold,
            "raw_score" : round(raw, 6),
        }

    def detect_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect anomalies for a list of metric dicts."""
        return [self.detect(r) for r in records]

    def detect_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run anomaly detection on a metrics DataFrame.
        Expects columns matching NUMERIC_FEATURES (extra columns are ignored).
        Returns the original DataFrame with added  anomaly  and  anomaly_score  columns.
        """
        results = self.detect_batch(df.to_dict(orient="records"))
        df = df.copy()
        df["anomaly"]       = [r["anomaly"] for r in results]
        df["anomaly_score"] = [r["score"]   for r in results]
        return df

    # ------------------------------------------------------------------
    # Feature construction
    # ------------------------------------------------------------------

    def _build_feature_vector(self, f: dict[str, Any]) -> pd.DataFrame:
        cpu      = float(f.get("cpu_util",    f.get("cpu",      30.0)))
        memory   = float(f.get("memory_util", f.get("memory",   40.0)))
        disk     = float(f.get("disk_util",   f.get("disk",     50.0)))
        net_in   = float(f.get("net_in_mbps",  100.0))
        net_out  = float(f.get("net_out_mbps",  80.0))
        latency  = float(f.get("latency_ms",  f.get("latency",  100.0)))
        err_rate = float(f.get("error_rate",  0.5))
        req_rate = float(f.get("request_rate", 500.0))
        gc_pause = float(f.get("gc_pause_ms",  20.0))
        threads  = float(f.get("thread_count", 50.0))
        tower    = str(f.get("tower", "Application"))

        # Rolling features — single-row prediction: use identity (no history)
        row = {
            "cpu_util":     cpu,
            "memory_util":  memory,
            "disk_util":    disk,
            "net_in_mbps":  net_in,
            "net_out_mbps": net_out,
            "latency_ms":   latency,
            "error_rate":   err_rate,
            "request_rate": req_rate,
            "gc_pause_ms":  gc_pause,
            "thread_count": threads,
            # Rolling cols: approximated by current value for single-row inference
            "cpu_util_roll3_mean":     cpu,
            "cpu_util_roll3_std":      0.0,
            "memory_util_roll3_mean":  memory,
            "memory_util_roll3_std":   0.0,
            "latency_ms_roll3_mean":   latency,
            "latency_ms_roll3_std":    0.0,
            "error_rate_roll3_mean":   err_rate,
            "error_rate_roll3_std":    0.0,
            # Interaction features
            "cpu_x_mem":   cpu * memory / 100,
            "net_ratio":   net_in / (net_out + 1),
            "latency_x_err": latency * err_rate / 100,
        }

        # Tower one-hot
        for t in self.TOWERS:
            row[f"tower_{t}"] = int(tower == t)

        return pd.DataFrame([row])


# ------------------------------------------------------------------
# FastAPI schema helpers
# ------------------------------------------------------------------

def anomaly_input_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "cpu":          {"type": "number", "description": "CPU utilisation %"},
            "memory":       {"type": "number", "description": "Memory utilisation %"},
            "disk":         {"type": "number", "description": "Disk utilisation %"},
            "latency":      {"type": "number", "description": "Latency in ms"},
            "error_rate":   {"type": "number", "description": "Error rate %"},
            "net_in_mbps":  {"type": "number", "description": "Network ingress Mbps"},
            "net_out_mbps": {"type": "number", "description": "Network egress Mbps"},
            "request_rate": {"type": "number", "description": "Requests per second"},
            "gc_pause_ms":  {"type": "number", "description": "GC pause ms"},
            "thread_count": {"type": "number", "description": "Active thread count"},
            "tower":        {"type": "string", "description": "Infrastructure tower"},
        },
        "required": ["cpu", "memory", "latency"],
    }


def anomaly_output_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "anomaly":   {"type": "boolean"},
            "score":     {"type": "number", "description": "Normalised anomaly score [0,1]"},
            "threshold": {"type": "number"},
            "raw_score": {"type": "number"},
        },
    }


# ------------------------------------------------------------------
# CLI smoke test
# ------------------------------------------------------------------
if __name__ == "__main__":
    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    predictor = AnomalyPredictor(
        model_path        = os.path.join(BASE, "models", "anomaly_model.pkl"),
        scaler_path       = os.path.join(BASE, "models", "scaler_anomaly.pkl"),
        score_params_path = os.path.join(BASE, "models", "anomaly_score_params.pkl"),
    )

    test_cases = [
        {"cpu": 95,  "memory": 92,  "latency": 8000,  "error_rate": 25.0},  # expect anomaly
        {"cpu": 30,  "memory": 45,  "latency": 120,   "error_rate": 0.5},   # expect normal
        {"cpu": 5,   "memory": 5,   "latency": 50000, "error_rate": 40.0},  # network outage
        {"cpu": 98,  "memory": 97,  "latency": 500,   "error_rate": 5.0},   # CPU/mem anomaly
        {"cpu": 25,  "memory": 35,  "latency": 200,   "error_rate": 0.3},   # normal
    ]
    print("\nAnomaly Predictor — smoke test")
    print("=" * 55)
    for tc in test_cases:
        result = predictor.detect(tc)
        flag = "🚨 ANOMALY" if result["anomaly"] else "✅ NORMAL"
        print(f"  {flag}  score={result['score']:.3f}  {tc}")
