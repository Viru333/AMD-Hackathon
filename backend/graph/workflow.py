"""
LangGraph workflow — wires together all seven nodes into a directed graph.

Topology
--------
incident_intake
    → anomaly_detection
    → severity_classification      (can run in parallel with anomaly)
    → root_cause_prediction
    → qdrant_retrieval
    → runbook_retrieval
    → rca_report_generator
    → END
"""
from __future__ import annotations
import logging
import time
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from backend.graph.state import IncidentState
from backend.graph.nodes import (
    incident_intake_node,
    anomaly_detection_node,
    severity_classification_node,
    root_cause_prediction_node,
    qdrant_retrieval_node,
    runbook_retrieval_node,
    rca_report_generator_node,
)

logger = logging.getLogger(__name__)

_graph = None


def _build_graph():
    """Compile the LangGraph StateGraph once."""
    builder = StateGraph(IncidentState)

    # Register nodes
    builder.add_node("intake",           incident_intake_node)
    builder.add_node("anomaly",          anomaly_detection_node)
    builder.add_node("severity",         severity_classification_node)
    builder.add_node("root_cause",       root_cause_prediction_node)
    builder.add_node("retrieval",        qdrant_retrieval_node)
    builder.add_node("runbooks",         runbook_retrieval_node)
    builder.add_node("report",           rca_report_generator_node)

    # Linear pipeline edges
    builder.set_entry_point("intake")
    builder.add_edge("intake",     "anomaly")
    builder.add_edge("anomaly",    "severity")
    builder.add_edge("severity",   "root_cause")
    builder.add_edge("root_cause", "retrieval")
    builder.add_edge("retrieval",  "runbooks")
    builder.add_edge("runbooks",   "report")
    builder.add_edge("report",     END)

    return builder.compile()


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
        logger.info("LangGraph workflow compiled ")
    return _graph


async def run_investigation(raw_input: Dict[str, Any], incident_id: str | None = None) -> IncidentState:
    """
    Execute the full investigation workflow and return the final state.

    Parameters
    ----------
    raw_input   : ObservabilityInput fields as a plain dict
    incident_id : optional pre-assigned incident ID
    """
    t_start = time.perf_counter()
    graph   = get_graph()

    initial_state: IncidentState = {
        "incident_id": incident_id or "",
        "raw_input":   raw_input,
        "timing":      {},
    }

    logger.info(f"Starting investigation workflow for {initial_state['incident_id'] or 'new incident'}")

    final_state: IncidentState = await graph.ainvoke(initial_state)

    total_ms = round((time.perf_counter() - t_start) * 1000, 1)
    final_state["timing"]["total"] = total_ms
    logger.info(f"Investigation complete in {total_ms} ms")

    return final_state
