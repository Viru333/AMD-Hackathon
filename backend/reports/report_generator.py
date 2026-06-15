"""
RCA Report Generator.

Produces both a structured JSON report and a Markdown narrative report
from the final LangGraph state.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from backend.graph.state import IncidentState


# ── Severity → emoji / colour label ──────────────────────────────
SEV_EMOJI = {
    "P1 Critical": "🔴",
    "P2 High":     "🟠",
    "P3 Medium":   "🟡",
    "P4 Low":      "🟢",
}

ANOMALY_ACTIONS = {
    True:  "Immediate investigation required — anomalous behaviour confirmed.",
    False: "No anomaly detected — behaviour is within normal baseline.",
}

RC_DESCRIPTION = {
    "Database Failure":          "Database layer is unreachable or severely degraded. Connection pooling, query timeouts, or replication issues are likely.",
    "Network Failure":           "Network connectivity is compromised. BGP routing, firewall ACL changes, or physical link failures are likely suspects.",
    "Memory Leak":               "A process is continuously growing its memory footprint without releasing it, leading to OOM conditions.",
    "CPU Saturation":            "One or more processes are consuming 100% of available CPU, starving other workloads.",
    "Disk Failure":              "Storage subsystem is degraded or failing. I/O errors, RAID degradation, or bad sectors detected.",
    "Service Crash":             "An application process terminated unexpectedly due to an unhandled exception, OOM kill, or dependency failure.",
    "Kubernetes Pod Failure":    "One or more pods are in a non-running state (CrashLoopBackOff, OOMKilled, Evicted, ImagePullBackOff).",
    "Cloud Resource Exhaustion": "Cloud provider service quotas have been reached. Provisioning of new resources is blocked.",
}


def generate_report(state: IncidentState) -> Tuple[Dict[str, Any], str]:
    """
    Build JSON and Markdown reports from the completed investigation state.

    Returns
    -------
    (report_json, report_markdown)
    """
    incident_id = state.get("incident_id", "UNKNOWN")
    raw         = state.get("raw_input", {})
    sev         = state.get("severity",  {})
    anom        = state.get("anomaly",   {})
    rc          = state.get("root_cause",{})
    similar     = state.get("similar_incidents", [])
    runbooks    = state.get("runbooks", [])
    now         = datetime.now(timezone.utc).isoformat()

    severity_label = sev.get("severity", "Unknown")
    root_cause_label = rc.get("root_cause", "Unknown")
    is_anomaly = anom.get("anomaly", False)

    # ─── Recommendations: runbook steps first, then top-3 similar resolutions ──
    recommendations = list(runbooks)
    for sim in similar[:2]:
        res = sim.get("resolution", "")
        if res and res not in recommendations:
            recommendations.append(f"[From {sim['incident_id']}] {res}")

    # ─── Structured JSON report ─────────────────────────────────────────────────
    report_json: Dict[str, Any] = {
        "incident_id":  incident_id,
        "generated_at": now,
        "incident_summary": {
            "tower":   raw.get("tower",   "Unknown"),
            "service": raw.get("service", "Unknown"),
            "description": raw.get("description", ""),
            "metrics": {
                "cpu_util_peak":    raw.get("cpu_util_peak",    0.0),
                "memory_util_peak": raw.get("memory_util_peak", 0.0),
                "disk_util_peak":   raw.get("disk_util_peak",   0.0),
                "latency_max_ms":   raw.get("latency_max_ms",   0.0),
                "error_count":      raw.get("error_count",      0),
            },
        },
        "severity": {
            "label":      severity_label,
            "confidence": sev.get("confidence", 0.0),
            "all_probabilities": sev.get("all_probabilities", {}),
        },
        "anomaly_detection": {
            "is_anomaly":     is_anomaly,
            "anomaly_score":  anom.get("score", 0.0),
            "threshold":      anom.get("threshold", 0.5),
            "action_required": ANOMALY_ACTIONS[is_anomaly],
        },
        "root_cause": {
            "predicted":    root_cause_label,
            "confidence":   rc.get("confidence", 0.0),
            "description":  RC_DESCRIPTION.get(root_cause_label, "See runbooks for investigation steps."),
            "top3_candidates": rc.get("top3", []),
            "all_probabilities": rc.get("all_probabilities", {}),
        },
        "similar_incidents": [
            {
                "incident_id": s["incident_id"],
                "summary":     s["summary"],
                "root_cause":  s["root_cause"],
                "resolution":  s["resolution"],
                "similarity":  s["score"],
            }
            for s in similar
        ],
        "recommendations": recommendations,
        "confidence_summary": {
            "severity_confidence":   sev.get("confidence", 0.0),
            "root_cause_confidence": rc.get("confidence", 0.0),
            "anomaly_score":         anom.get("score", 0.0),
            "overall_confidence":    round(
                (sev.get("confidence", 0) + rc.get("confidence", 0)) / 2, 4
            ),
        },
    }

    # ─── Markdown report ────────────────────────────────────────────────────────
    sev_emoji    = SEV_EMOJI.get(severity_label, "⚪")
    anom_emoji   = "ALERT" if is_anomaly else "SAFE"
    rc_conf_pct  = round(rc.get("confidence", 0.0) * 100, 1)
    sev_conf_pct = round(sev.get("confidence", 0.0) * 100, 1)

    similar_md = ""
    for s in similar[:3]:
        similar_md += (
            f"\n- **{s['incident_id']}** (similarity: {s['score']:.2f})  \n"
            f"  *{s['summary']}*  \n"
            f"  Resolution: {s['resolution']}\n"
        )
    if not similar_md:
        similar_md = "\n- No similar incidents found in knowledge base.\n"

    recs_md = "\n".join(f"{i+1}. {r}" for i, r in enumerate(recommendations))

    top3_md = ""
    for c in rc.get("top3", []):
        pct = round(c["confidence"] * 100, 1)
        top3_md += f"  - {c['root_cause']}: **{pct}%**\n"

    report_markdown = f"""# RCA Report — {incident_id}

**Generated:** {now}  
**Tower:** {raw.get("tower", "Unknown")} | **Service:** {raw.get("service", "Unknown")}

---

## 1. Incident Summary

| Metric | Value |
|--------|-------|
| CPU Peak | {raw.get("cpu_util_peak", 0.0):.1f}% |
| Memory Peak | {raw.get("memory_util_peak", 0.0):.1f}% |
| Disk Peak | {raw.get("disk_util_peak", 0.0):.1f}% |
| Max Latency | {raw.get("latency_max_ms", 0.0):.0f} ms |
| Error Count | {raw.get("error_count", 0):,} |

{f'> **Description:** {raw["description"]}' if raw.get("description") else ""}

---

## 2. Severity Assessment

{sev_emoji} **{severity_label}** — Confidence: {sev_conf_pct}%

| Class | Probability |
|-------|------------|
{"".join(f"| {k} | {v*100:.1f}% |{chr(10)}" for k, v in sev.get("all_probabilities", {}).items())}

---

## 3. Anomaly Detection

{anom_emoji} **{'ANOMALY DETECTED' if is_anomaly else 'No Anomaly'}**  
Anomaly Score: **{anom.get("score", 0.0):.3f}** / 1.000 (threshold: {anom.get("threshold", 0.5)})

{ANOMALY_ACTIONS[is_anomaly]}

---

## 4. Root Cause Analysis

**Predicted Root Cause: {root_cause_label}** — Confidence: {rc_conf_pct}%

{RC_DESCRIPTION.get(root_cause_label, "")}

**Top Candidates:**
{top3_md}

---

## 5. Similar Historical Incidents
{similar_md}

---

## 6. Recommended Resolution Steps

{recs_md}

---

## 7. Confidence Summary

| Model | Confidence |
|-------|-----------|
| Severity Classifier | {sev_conf_pct}% |
| Root Cause Predictor | {rc_conf_pct}% |
| Anomaly Score | {anom.get("score", 0.0)*100:.1f}% |
| **Overall** | **{round((sev.get("confidence",0)+rc.get("confidence",0))/2*100,1)}%** |

---

*Report auto-generated by Unified Agentic Observability Platform*
"""

    return report_json, report_markdown
