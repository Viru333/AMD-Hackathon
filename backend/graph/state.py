"""
LangGraph state definition — the shared dict that flows through every node.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class IncidentState(TypedDict, total=False):
    # ── Input ────────────────────────────────────────────────────
    incident_id:   str
    raw_input:     Dict[str, Any]      # raw ObservabilityInput fields
    description:   Optional[str]       # free-text description if provided

    # ── ML predictions ──────────────────────────────────────────
    anomaly:       Dict[str, Any]      # {anomaly, score, threshold, raw_score}
    severity:      Dict[str, Any]      # {severity, confidence, all_probabilities}
    root_cause:    Dict[str, Any]      # {root_cause, confidence, top3, all_probabilities}

    # ── Retrieval ────────────────────────────────────────────────
    similar_incidents: List[Dict[str, Any]]   # from Qdrant
    runbooks:          List[str]              # actionable steps

    # ── Report ──────────────────────────────────────────────────
    report:            Dict[str, Any]         # structured JSON report
    report_markdown:   str                    # markdown version

    # ── Meta ────────────────────────────────────────────────────
    error:         Optional[str]       # any pipeline error
    timing:        Dict[str, float]    # node timing in ms
