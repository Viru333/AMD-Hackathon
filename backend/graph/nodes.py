"""
LangGraph node implementations.
Each node receives IncidentState, updates specific keys, and returns the state.
"""
from __future__ import annotations
import logging
import time
import uuid
from typing import Any, Dict

from backend.graph.state import IncidentState
from backend.ml.inference import get_models
from backend.vector_store.retrieval import retrieve_similar_incidents, get_runbooks
from backend.reports.report_generator import generate_report

logger = logging.getLogger(__name__)


def _timer(state: IncidentState, key: str, t0: float) -> None:
    timing = state.get("timing", {})
    timing[key] = round((time.perf_counter() - t0) * 1000, 1)
    state["timing"] = timing


# ══════════════════════════════════════════════════════════════════
# Node 1 — Incident Intake
# ══════════════════════════════════════════════════════════════════

def incident_intake_node(state: IncidentState) -> IncidentState:
    """
    Assign a unique incident ID if one wasn't provided.
    Normalise raw input keys so downstream nodes see a consistent shape.
    """
    t0 = time.perf_counter()
    logger.info("[Node] incident_intake")

    raw = state.get("raw_input", {})

    # Assign ID
    if not state.get("incident_id"):
        state["incident_id"] = f"INC-{uuid.uuid4().hex[:8].upper()}"

    # Key normalisation — accept both  cpu_usage  and  cpu
    normalised: Dict[str, Any] = {}
    normalised["cpu_util_peak"]    = float(raw.get("cpu_usage",    raw.get("cpu",    40.0)))
    normalised["memory_util_peak"] = float(raw.get("memory_usage", raw.get("memory", 50.0)))
    normalised["disk_util_peak"]   = float(raw.get("disk_usage",   raw.get("disk",   50.0)))
    normalised["latency_max_ms"]   = float(raw.get("latency_ms",   raw.get("latency", 200.0)))
    normalised["latency_ms"]       = normalised["latency_max_ms"]
    normalised["cpu_util"]         = normalised["cpu_util_peak"]
    normalised["memory_util"]      = normalised["memory_util_peak"]
    normalised["disk_util"]        = normalised["disk_util_peak"]
    normalised["error_count"]      = int(raw.get("error_count",  5))
    normalised["warn_count"]       = int(raw.get("warn_count",  20))
    normalised["info_count"]       = int(raw.get("info_count", 100))
    normalised["alert_volume"]     = int(raw.get("alert_volume", 3))
    normalised["duration_min"]     = float(raw.get("duration_min", 30.0))
    normalised["impacted_services"]= int(raw.get("impacted_services", 1))
    normalised["error_rate"]       = float(raw.get("error_rate", max(0.5, normalised["error_count"] / 100)))
    normalised["net_in_mbps"]      = float(raw.get("net_in_mbps", 100.0))
    normalised["net_out_mbps"]     = float(raw.get("net_out_mbps", 80.0))
    normalised["request_rate"]     = float(raw.get("request_rate", 500.0))
    normalised["gc_pause_ms"]      = float(raw.get("gc_pause_ms", 20.0))
    normalised["thread_count"]     = float(raw.get("thread_count", 50.0))
    normalised["tower"]            = str(raw.get("tower", "Application"))
    normalised["service"]          = str(raw.get("service", "api-gateway"))
    normalised["description"]      = raw.get("description", "")

    state["raw_input"] = normalised
    state["description"] = normalised["description"]
    _timer(state, "intake", t0)
    return state


# ══════════════════════════════════════════════════════════════════
# Node 2 — Anomaly Detection
# ══════════════════════════════════════════════════════════════════

def anomaly_detection_node(state: IncidentState) -> IncidentState:
    """Run Isolation Forest anomaly detection on the normalised input."""
    t0 = time.perf_counter()
    logger.info("[Node] anomaly_detection")
    try:
        result = get_models().detect_anomaly(state["raw_input"])
        state["anomaly"] = result
        logger.info(f"  anomaly={result['anomaly']}  score={result['score']:.3f}")
    except Exception as e:
        logger.error(f"  anomaly_detection_node error: {e}")
        state["anomaly"] = {"anomaly": False, "score": 0.0, "threshold": 0.5, "raw_score": 0.0}
    _timer(state, "anomaly_detection", t0)
    return state


# ══════════════════════════════════════════════════════════════════
# Node 3 — Severity Classification
# ══════════════════════════════════════════════════════════════════

def severity_classification_node(state: IncidentState) -> IncidentState:
    """Run XGBoost severity classification."""
    t0 = time.perf_counter()
    logger.info("[Node] severity_classification")
    try:
        result = get_models().predict_severity(state["raw_input"])
        state["severity"] = result
        logger.info(f"  severity={result['severity']}  conf={result['confidence']:.3f}")
    except Exception as e:
        logger.error(f"  severity_classification_node error: {e}")
        state["severity"] = {"severity": "P2 High", "confidence": 0.5, "all_probabilities": {}}
    _timer(state, "severity_classification", t0)
    return state


# ══════════════════════════════════════════════════════════════════
# Node 4 — Root Cause Prediction
# ══════════════════════════════════════════════════════════════════

def root_cause_prediction_node(state: IncidentState) -> IncidentState:
    """Run XGBoost root cause prediction."""
    t0 = time.perf_counter()
    logger.info("[Node] root_cause_prediction")
    try:
        result = get_models().predict_root_cause(state["raw_input"])
        state["root_cause"] = result
        logger.info(f"  root_cause={result['root_cause']}  conf={result['confidence']:.3f}")
    except Exception as e:
        logger.error(f"  root_cause_prediction_node error: {e}")
        state["root_cause"] = {
            "root_cause": "Unknown", "confidence": 0.0, "top3": [], "all_probabilities": {}
        }
    _timer(state, "root_cause_prediction", t0)
    return state


# ══════════════════════════════════════════════════════════════════
# Node 5 — Qdrant Retrieval
# ══════════════════════════════════════════════════════════════════

def qdrant_retrieval_node(state: IncidentState) -> IncidentState:
    """Find the most similar historical incidents from the knowledge base."""
    t0 = time.perf_counter()
    logger.info("[Node] qdrant_retrieval")
    try:
        query_incident = {
            **state["raw_input"],
            "incident_id": state["incident_id"],
            "severity":    state.get("severity", {}).get("severity", ""),
            "root_cause":  state.get("root_cause", {}).get("root_cause", ""),
        }
        similar = retrieve_similar_incidents(query_incident, top_k=5)
        state["similar_incidents"] = similar
        logger.info(f"  retrieved {len(similar)} similar incidents")
    except Exception as e:
        logger.error(f"  qdrant_retrieval_node error: {e}")
        state["similar_incidents"] = []
    _timer(state, "qdrant_retrieval", t0)
    return state


# ══════════════════════════════════════════════════════════════════
# Node 6 — Runbook Retrieval
# ══════════════════════════════════════════════════════════════════

def runbook_retrieval_node(state: IncidentState) -> IncidentState:
    """Look up actionable runbook steps for the predicted root cause."""
    t0 = time.perf_counter()
    logger.info("[Node] runbook_retrieval")
    try:
        rc        = state.get("root_cause", {}).get("root_cause", "Unknown")
        runbooks  = get_runbooks(rc, top_k=6)
        state["runbooks"] = runbooks
        logger.info(f"  {len(runbooks)} runbook steps for '{rc}'")
    except Exception as e:
        logger.error(f"  runbook_retrieval_node error: {e}")
        state["runbooks"] = ["Review recent infrastructure changes", "Escalate to on-call"]
    _timer(state, "runbook_retrieval", t0)
    return state


# ══════════════════════════════════════════════════════════════════
# Node 7 — RCA Report Generator
# ══════════════════════════════════════════════════════════════════

def rca_report_generator_node(state: IncidentState) -> IncidentState:
    """Synthesise all findings into a structured JSON + Markdown report."""
    t0 = time.perf_counter()
    logger.info("[Node] rca_report_generator")
    try:
        report_json, report_md = generate_report(state)
        state["report"]          = report_json
        state["report_markdown"] = report_md
        logger.info("  Report generated")
    except Exception as e:
        logger.error(f"  rca_report_generator_node error: {e}")
        state["report"]          = {"error": str(e)}
        state["report_markdown"] = f"# Report Generation Error\n\n{e}"
    _timer(state, "rca_report_generator", t0)
    return state
