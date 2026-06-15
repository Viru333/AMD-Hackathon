"""
CRUD operations for incident records.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import List, Optional

from backend.database.models import IncidentModel, get_session
from backend.graph.state import IncidentState

logger = logging.getLogger(__name__)


def save_incident(state: IncidentState) -> bool:
    """Persist the full investigation result to the database."""
    try:
        raw          = state.get("raw_input", {})
        severity_res = state.get("severity",  {})
        anomaly_res  = state.get("anomaly",   {})
        rca_res      = state.get("root_cause",{})
        similar      = state.get("similar_incidents", [])
        similar_ids  = ",".join(s.get("incident_id", "") for s in similar)

        record = IncidentModel(
            incident_id           = state["incident_id"],
            timestamp             = datetime.utcnow(),
            severity              = severity_res.get("severity", "Unknown"),
            severity_confidence   = severity_res.get("confidence", 0.0),
            anomaly               = anomaly_res.get("anomaly", False),
            anomaly_score         = anomaly_res.get("score", 0.0),
            root_cause            = rca_res.get("root_cause", "Unknown"),
            root_cause_confidence = rca_res.get("confidence", 0.0),
            tower                 = raw.get("tower", ""),
            service               = raw.get("service", ""),
            cpu_usage             = raw.get("cpu_util_peak", 0.0),
            memory_usage          = raw.get("memory_util_peak", 0.0),
            disk_usage            = raw.get("disk_util_peak", 0.0),
            error_count           = int(raw.get("error_count", 0)),
            latency_ms            = raw.get("latency_max_ms", 0.0),
            report_json           = json.dumps(state.get("report", {})),
            report_markdown       = state.get("report_markdown", ""),
            similar_incident_ids  = similar_ids,
        )

        with get_session() as session:
            existing = session.get(IncidentModel, state["incident_id"])
            if existing:
                for attr in ["severity", "severity_confidence", "anomaly", "anomaly_score",
                             "root_cause", "root_cause_confidence", "report_json",
                             "report_markdown", "similar_incident_ids"]:
                    setattr(existing, attr, getattr(record, attr))
                session.commit()
            else:
                session.add(record)
                session.commit()

        logger.info(f"Incident {state['incident_id']} saved to DB")
        return True
    except Exception as e:
        logger.error(f"save_incident error: {e}")
        return False


def get_incident(incident_id: str) -> Optional[dict]:
    """Fetch a single incident by ID."""
    try:
        with get_session() as session:
            rec = session.get(IncidentModel, incident_id)
            if not rec:
                return None
            return _to_dict(rec)
    except Exception as e:
        logger.error(f"get_incident error: {e}")
        return None


def list_incidents(
    limit: int = 50,
    offset: int = 0,
    severity: Optional[str] = None,
    root_cause: Optional[str] = None,
    anomaly_only: bool = False,
) -> tuple[int, List[dict]]:
    """List incidents with optional filters. Returns (total, records)."""
    try:
        from sqlalchemy import select, func
        with get_session() as session:
            stmt = select(IncidentModel)
            if severity:
                stmt = stmt.where(IncidentModel.severity == severity)
            if root_cause:
                stmt = stmt.where(IncidentModel.root_cause == root_cause)
            if anomaly_only:
                stmt = stmt.where(IncidentModel.anomaly == True)  # noqa: E712
            stmt = stmt.order_by(IncidentModel.timestamp.desc())

            total = session.execute(
                select(func.count()).select_from(stmt.subquery())
            ).scalar() or 0

            records = session.execute(stmt.offset(offset).limit(limit)).scalars().all()
            return int(total), [_to_dict(r) for r in records]
    except Exception as e:
        logger.error(f"list_incidents error: {e}")
        return 0, []


def _to_dict(rec: IncidentModel) -> dict:
    return {
        "incident_id":           rec.incident_id,
        "timestamp":             rec.timestamp.isoformat() if rec.timestamp else None,
        "severity":              rec.severity,
        "severity_confidence":   rec.severity_confidence,
        "anomaly":               rec.anomaly,
        "anomaly_score":         rec.anomaly_score,
        "root_cause":            rec.root_cause,
        "root_cause_confidence": rec.root_cause_confidence,
        "tower":                 rec.tower,
        "service":               rec.service,
        "cpu_usage":             rec.cpu_usage,
        "memory_usage":          rec.memory_usage,
        "disk_usage":            rec.disk_usage,
        "error_count":           rec.error_count,
        "latency_ms":            rec.latency_ms,
        "report_json":           rec.report_json,
        "report_markdown":       rec.report_markdown,
        "similar_incident_ids":  rec.similar_incident_ids,
    }
