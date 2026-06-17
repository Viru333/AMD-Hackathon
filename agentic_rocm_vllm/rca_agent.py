"""
Agentic RCA narrative generator powered by an LLM served via vLLM on ROCm.

The existing backend (`backend/reports/report_generator.py`) builds the RCA
report from fixed templates. This module is the *agentic* upgrade: it feeds
the ML model outputs (severity, anomaly, root cause), the retrieved similar
incidents and runbooks into an LLM and asks it to reason over them and write
the narrative, recommendations and next steps.

It is intentionally decoupled:

  * It accepts a plain dict (the same shape the LangGraph state already has),
    so it can be wired in as a drop-in node WITHOUT importing backend code.
  * If vLLM is unreachable and FALLBACK_ON_ERROR is set, it returns a simple
    deterministic template so demos never hard-fail.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Dict, List

from . import config
from .vllm_client import chat, VLLMUnavailable

logger = logging.getLogger("agentic_rocm_vllm.agent")

SYSTEM_PROMPT = (
    "You are a senior Site Reliability Engineer acting as an automated "
    "incident root-cause-analysis agent. You are given the structured output "
    "of ML models (severity classifier, anomaly detector, root-cause "
    "predictor), plus similar past incidents and runbook hints. Reason over "
    "this evidence and produce a clear, actionable RCA report in Markdown. "
    "Be concise and specific. Never invent metrics that were not provided."
)

REPORT_INSTRUCTIONS = (
    "Write a Markdown RCA report with these sections:\n"
    "1. **Executive Summary** (2-3 sentences)\n"
    "2. **Severity & Anomaly Assessment** (interpret the scores)\n"
    "3. **Most Likely Root Cause** (justify using the evidence)\n"
    "4. **Recommended Remediation** (ordered, concrete steps)\n"
    "5. **Similar Past Incidents** (what we can learn from them)\n"
)


def _build_user_prompt(evidence: Dict[str, Any]) -> str:
    return (
        "Here is the incident evidence as JSON:\n\n"
        f"```json\n{json.dumps(evidence, indent=2, default=str)}\n```\n\n"
        f"{REPORT_INSTRUCTIONS}"
    )


def _fallback_report(evidence: Dict[str, Any]) -> str:
    sev = evidence.get("severity", {}).get("label", "Unknown")
    rc = evidence.get("root_cause", {}).get("predicted", "Unknown")
    anom = evidence.get("anomaly", {}).get("is_anomaly", False)
    return (
        f"# RCA Report (template fallback)\n\n"
        f"**Severity:** {sev}\n\n"
        f"**Anomaly:** {'Detected' if anom else 'Normal'}\n\n"
        f"**Most Likely Root Cause:** {rc}\n\n"
        "_vLLM was unavailable, so this is a non-agentic fallback. "
        "Start the vLLM server to get a full LLM-generated narrative._"
    )


def generate_rca_report(evidence: Dict[str, Any]) -> str:
    """
    Generate the RCA narrative (Markdown) from the evidence dict.

    `evidence` is expected to contain keys like `severity`, `anomaly`,
    `root_cause`, `similar_incidents`, `runbooks` — exactly the artefacts the
    existing pipeline already computes.
    """
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(evidence)},
    ]
    try:
        report = chat(messages)
        logger.info("Generated agentic RCA report (%d chars)", len(report))
        return report
    except VLLMUnavailable:
        if config.FALLBACK_ON_ERROR:
            logger.warning("Falling back to template RCA report")
            return _fallback_report(evidence)
        raise


# ──────────────────────────────────────────────────────────────────
# Optional LangGraph drop-in node.
#
# To make the EXISTING pipeline agentic without editing backend code,
# you can register this node in place of `rca_report_generator_node`:
#
#     from agentic_rocm_vllm.rca_agent import agentic_report_node
#     builder.add_node("report", agentic_report_node)
#
# It reads/writes the same state dict keys the current graph uses.
# ──────────────────────────────────────────────────────────────────
def agentic_report_node(state: Dict[str, Any]) -> Dict[str, Any]:
    evidence = {
        "incident_id": state.get("incident_id"),
        "raw_input": state.get("raw_input", {}),
        "severity": state.get("severity", {}),
        "anomaly": state.get("anomaly", {}),
        "root_cause": state.get("root_cause", {}),
        "similar_incidents": state.get("similar_incidents", []),
        "runbooks": state.get("runbooks", []),
    }
    markdown = generate_rca_report(evidence)
    report = dict(state.get("report", {}))
    report["markdown"] = markdown
    report["generated_by"] = f"vllm:{config.VLLM_MODEL}"
    state["report"] = report
    return state
