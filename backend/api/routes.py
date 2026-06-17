"""
FastAPI route handlers.
"""
from __future__ import annotations
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from backend.api.schemas import (
    AnomalyRequest, AnomalyResponse,
    HealthResponse, IncidentListResponse, IncidentRecord,
    InvestigateRequest, InvestigateResponse,
    RootCauseCandidate, RootCauseRequest, RootCauseResponse,
    RootResponse,
    SeverityRequest, SeverityResponse,
    SimilarIncident,
)
from backend.ml.inference import get_models
from backend.graph.workflow import run_investigation
from backend.database.storage import save_incident, get_incident, list_incidents
from backend.vector_store.qdrant_client import get_collection_info

logger = logging.getLogger(__name__)
router = APIRouter()


# ══════════════════════════════════════════════════════════════════
# Root & Health
# ══════════════════════════════════════════════════════════════════

@router.get("/", response_model=RootResponse, tags=["Info"])
async def root():
    return {
        "name":        "Unified Agentic Observability Platform",
        "description": "AI backend for anomaly detection, severity classification, and root cause analysis",
        "version":     "1.0.0",
        "docs_url":    "/docs",
    }


@router.get("/health", response_model=HealthResponse, tags=["Info"])
async def health():
    models  = get_models()
    qdrant  = get_collection_info()

    return {
        "status":    "ok",
        "version":   "1.0.0",
        "models": {
            "severity":  "loaded" if models.severity_model  else "unavailable",
            "anomaly":   "loaded" if models.anomaly_model   else "unavailable",
            "rca":       "loaded" if models.rca_model       else "unavailable",
        },
        "vector_db": f"{qdrant['status']} ({qdrant['vectors_count']} docs)",
        "database":  "connected",
    }


# ══════════════════════════════════════════════════════════════════
# Individual ML endpoints
# ══════════════════════════════════════════════════════════════════

@router.post("/predict/severity", response_model=SeverityResponse, tags=["ML Predictions"])
async def predict_severity(body: SeverityRequest):
    """
    Predict incident severity (P1–P4) from observability metrics.
    """
    try:
        result = get_models().predict_severity(body.model_dump())
        return result
    except Exception as e:
        logger.error(f"/predict/severity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/anomaly", response_model=AnomalyResponse, tags=["ML Predictions"])
async def predict_anomaly(body: AnomalyRequest):
    """
    Detect whether current metrics represent anomalous infrastructure behaviour.
    """
    try:
        result = get_models().detect_anomaly(body.model_dump())
        return result
    except Exception as e:
        logger.error(f"/predict/anomaly error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/root-cause", response_model=RootCauseResponse, tags=["ML Predictions"])
async def predict_root_cause(body: RootCauseRequest):
    """
    Predict the most probable root cause of an incident.
    """
    try:
        result  = get_models().predict_root_cause(body.model_dump())
        top3    = [RootCauseCandidate(**c) for c in result.get("top3", [])]
        return RootCauseResponse(
            root_cause        = result["root_cause"],
            confidence        = result["confidence"],
            top3              = top3,
            all_probabilities = result.get("all_probabilities", {}),
        )
    except Exception as e:
        logger.error(f"/predict/root-cause error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# Full LangGraph investigation
# ══════════════════════════════════════════════════════════════════

@router.post("/investigate", response_model=InvestigateResponse, tags=["Investigation"])
async def investigate(body: InvestigateRequest):
    """
    Run the full LangGraph investigation pipeline:
    Intake → Anomaly → Severity → Root Cause → Retrieval → Runbooks → Report.
    """
    t0 = time.perf_counter()
    try:
        raw_input = body.model_dump()
        state     = await run_investigation(
            raw_input=raw_input,
            incident_id=body.incident_id,
        )

        # Persist to DB + vector store
        save_incident(state)

        sev  = state.get("severity",   {})
        anom = state.get("anomaly",    {})
        rc   = state.get("root_cause", {})
        sim  = state.get("similar_incidents", [])
        rpt  = state.get("report", {})

        similar_out = [
            SimilarIncident(
                incident_id=s["incident_id"],
                summary=s["summary"],
                root_cause=s["root_cause"],
                resolution=s["resolution"],
                score=s["score"],
            )
            for s in sim
        ]

        total_ms = round((time.perf_counter() - t0) * 1000, 1)

        return InvestigateResponse(
            incident_id            = state["incident_id"],
            severity               = sev.get("severity",  "Unknown"),
            severity_confidence    = sev.get("confidence", 0.0),
            anomaly                = anom.get("anomaly", False),
            anomaly_score          = anom.get("score",   0.0),
            root_cause             = rc.get("root_cause", "Unknown"),
            root_cause_confidence  = rc.get("confidence", 0.0),
            similar_incidents      = similar_out,
            recommendations        = rpt.get("recommendations", []),
            report                 = json.dumps(rpt, indent=2),
            report_markdown        = state.get("report_markdown", ""),
            processing_time_ms     = total_ms,
        )

    except Exception as e:
        logger.error(f"/investigate error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# Incident CRUD
# ══════════════════════════════════════════════════════════════════

@router.get("/incidents", response_model=IncidentListResponse, tags=["Incidents"])
async def list_incidents_endpoint(
    limit:        int           = Query(50, ge=1, le=200),
    offset:       int           = Query(0,  ge=0),
    severity:     Optional[str] = Query(None),
    root_cause:   Optional[str] = Query(None),
    anomaly_only: bool          = Query(False),
):
    """
    List stored incidents with optional filters.
    """
    total, records = list_incidents(
        limit=limit, offset=offset,
        severity=severity, root_cause=root_cause, anomaly_only=anomaly_only,
    )
    incident_records = []
    for r in records:
        incident_records.append(IncidentRecord(
            incident_id           = r["incident_id"],
            timestamp             = r["timestamp"],
            severity              = r["severity"],
            severity_confidence   = r["severity_confidence"],
            anomaly               = r["anomaly"],
            anomaly_score         = r["anomaly_score"],
            root_cause            = r["root_cause"],
            root_cause_confidence = r["root_cause_confidence"],
            tower                 = r["tower"],
            service               = r["service"],
            cpu_usage             = r["cpu_usage"],
            memory_usage          = r["memory_usage"],
            disk_usage            = r["disk_usage"],
            error_count           = r["error_count"],
            report_summary        = r.get("report_json", "")[:200],
        ))
    return IncidentListResponse(total=total, incidents=incident_records)


@router.get("/incident/{incident_id}", tags=["Incidents"])
async def get_incident_endpoint(incident_id: str):
    """
    Retrieve a single incident record by ID.
    """
    record = get_incident(incident_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    # Parse stored report_json
    try:
        record["report"] = json.loads(record.get("report_json", "{}"))
    except Exception:
        record["report"] = {}
    return record


@router.get("/rca-report/{incident_id}", tags=["Incidents"])
async def get_rca_report(
    incident_id: str,
    format: str = Query("json", enum=["json", "markdown"]),
):
    """
    Retrieve the RCA report for a stored incident.
    Use ?format=markdown for the Markdown narrative version.
    """
    record = get_incident(incident_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    if format == "markdown":
        md = record.get("report_markdown", "No markdown report available.")
        return PlainTextResponse(md, media_type="text/markdown")

    try:
        return json.loads(record.get("report_json", "{}"))
    except Exception:
        return {"error": "Report not available"}
