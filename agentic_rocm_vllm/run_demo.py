"""
Standalone demo for the ROCm + vLLM agentic RCA layer.

Run (after starting a vLLM server — see serve_vllm.sh):

    python -m agentic_rocm_vllm.run_demo

If the vLLM server is not running and VLLM_FALLBACK_ON_ERROR=true (default),
this prints a template report instead so you can verify the wiring offline.
"""
from __future__ import annotations
import logging

from .rca_agent import generate_rca_report
from .vllm_client import health_check
from . import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

# A sample evidence bundle, exactly the shape the existing pipeline produces.
SAMPLE_EVIDENCE = {
    "incident_id": "INC-DEMO-001",
    "raw_input": {
        "tower": "Application",
        "service": "payment-service",
        "cpu_usage": 96,
        "memory_usage": 91,
        "error_count": 180,
        "latency_ms": 2400,
        "description": "Checkout failures spiking in Circle 1 / BA1",
    },
    "severity": {"label": "P1 Critical", "confidence": 0.93,
                 "all_probabilities": {"P1 Critical": 0.93, "P2 High": 0.05}},
    "anomaly": {"is_anomaly": True, "anomaly_score": 0.88, "threshold": 0.5},
    "root_cause": {
        "predicted": "Database Failure",
        "confidence": 0.81,
        "top3_candidates": [
            {"root_cause": "Database Failure", "confidence": 0.81},
            {"root_cause": "CPU Saturation", "confidence": 0.11},
        ],
    },
    "similar_incidents": [
        {"incident_id": "INC-000147", "summary": "DB connection pool exhausted",
         "root_cause": "Database Failure",
         "resolution": "Restart DB service; check replication lag", "score": 0.92},
    ],
    "runbooks": [
        "Check primary DB health and failover status",
        "Scale read replicas; throttle write traffic",
    ],
}


def main() -> None:
    print(f"vLLM endpoint : {config.VLLM_BASE_URL}")
    print(f"vLLM model    : {config.VLLM_MODEL}")
    print(f"server up?    : {health_check()}\n")

    report = generate_rca_report(SAMPLE_EVIDENCE)
    print("=" * 70)
    print(report)
    print("=" * 70)


if __name__ == "__main__":
    main()
