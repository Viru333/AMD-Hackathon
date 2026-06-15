"""
Feature engineering helpers — mirrors ml_project/02_feature_engineering.py
so the backend can construct the exact feature vectors the models expect.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Any


TOWERS = ["Compute", "Storage", "Network", "Database", "Cloud", "Application"]
SERVICES = [
    "auth-service", "payment-gateway", "order-service", "inventory-api",
    "notification-service", "reporting-service", "analytics-engine",
    "cache-cluster", "message-broker", "api-gateway",
]


def build_severity_features(f: dict[str, Any]) -> pd.DataFrame:
    """
    Construct a single-row feature DataFrame compatible with the severity model.
    Accepts raw keys from ObservabilityInput or SeverityRequest.
    """
    cpu      = float(f.get("cpu_util_peak",    f.get("cpu_usage",    f.get("cpu",    40.0))))
    memory   = float(f.get("memory_util_peak", f.get("memory_usage", f.get("memory", 50.0))))
    disk     = float(f.get("disk_util_peak",   f.get("disk_usage",   f.get("disk",   50.0))))
    latency  = float(f.get("latency_max_ms",   f.get("latency_ms",   f.get("latency", 200.0))))
    errors   = float(f.get("error_count",       5.0))
    warns    = float(f.get("warn_count",        20.0))
    infos    = float(f.get("info_count",        100.0))
    duration = float(f.get("duration_min",      30.0))
    alert_vol= float(f.get("alert_volume",      3.0))
    impacted = float(f.get("impacted_services", 1.0))
    tower    = str(f.get("tower",    "Application"))
    service  = str(f.get("service",  "api-gateway"))

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
        # derived
        "error_warn_ratio": errors / (warns + 1),
        "alert_per_hour":   alert_vol / (duration / 60 + 0.01),
        "composite_load":   cpu * 0.4 + memory * 0.3 + disk * 0.3,
        "log_error_count":  np.log1p(errors),
        "log_latency":      np.log1p(latency),
    }

    for t in TOWERS:
        row[f"tower_{t}"] = int(tower == t)
    for s in SERVICES:
        row[f"svc_{s}"] = int(service == s)

    return pd.DataFrame([row])


def build_anomaly_features(f: dict[str, Any]) -> pd.DataFrame:
    """
    Construct a single-row feature DataFrame compatible with the anomaly model.
    """
    cpu      = float(f.get("cpu_util",    f.get("cpu_usage",    f.get("cpu",    30.0))))
    memory   = float(f.get("memory_util", f.get("memory_usage", f.get("memory", 40.0))))
    disk     = float(f.get("disk_util",   f.get("disk_usage",   f.get("disk",   50.0))))
    net_in   = float(f.get("net_in_mbps",  100.0))
    net_out  = float(f.get("net_out_mbps",  80.0))
    latency  = float(f.get("latency_ms",  f.get("latency",  100.0)))
    err_rate = float(f.get("error_rate",  0.5))
    req_rate = float(f.get("request_rate", 500.0))
    gc_pause = float(f.get("gc_pause_ms",  20.0))
    threads  = float(f.get("thread_count", 50.0))
    tower    = str(f.get("tower", "Application"))

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
        # rolling features — approximate with current value for single-row
        "cpu_util_roll3_mean":     cpu,
        "cpu_util_roll3_std":      0.0,
        "memory_util_roll3_mean":  memory,
        "memory_util_roll3_std":   0.0,
        "latency_ms_roll3_mean":   latency,
        "latency_ms_roll3_std":    0.0,
        "error_rate_roll3_mean":   err_rate,
        "error_rate_roll3_std":    0.0,
        # interaction features
        "cpu_x_mem":     cpu * memory / 100,
        "net_ratio":     net_in / (net_out + 1),
        "latency_x_err": latency * err_rate / 100,
    }

    for t in TOWERS:
        row[f"tower_{t}"] = int(tower == t)

    return pd.DataFrame([row])


# build_rca_features is identical to build_severity_features
build_rca_features = build_severity_features
