"""
Pydantic request / response schemas for all API endpoints.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════
# Shared input payload
# ══════════════════════════════════════════════════════════════════

class ObservabilityInput(BaseModel):
    """Raw observability signals — the canonical input for all ML endpoints."""
    # Core metrics (required for meaningful prediction)
    cpu_usage:    float = Field(..., ge=0, le=100,  description="CPU utilisation %")
    memory_usage: float = Field(..., ge=0, le=100,  description="Memory utilisation %")
    disk_usage:   float = Field(50.0, ge=0, le=100, description="Disk utilisation %")
    error_count:  int   = Field(...,  ge=0,          description="Error log count")

    # Optional enrichments
    warn_count:        int   = Field(20,    ge=0)
    alert_volume:      int   = Field(3,     ge=0)
    duration_min:      float = Field(30.0,  ge=0)
    impacted_services: int   = Field(1,     ge=1)
    latency_ms:        float = Field(200.0, ge=0, description="Max latency in ms")
    error_rate:        float = Field(0.5,   ge=0, description="Error rate %")
    net_in_mbps:       float = Field(100.0, ge=0)
    net_out_mbps:      float = Field(80.0,  ge=0)
    request_rate:      float = Field(500.0, ge=0)
    gc_pause_ms:       float = Field(20.0,  ge=0)
    thread_count:      float = Field(50.0,  ge=0)

    # Context
    tower:   str = Field("Application", description="Infrastructure tower")
    service: str = Field("api-gateway",  description="Affected service name")

    model_config = {"json_schema_extra": {
        "example": {
            "cpu_usage": 95, "memory_usage": 88,
            "disk_usage": 72, "error_count": 54,
            "tower": "Database", "service": "order-service",
        }
    }}


# ══════════════════════════════════════════════════════════════════
# Severity
# ══════════════════════════════════════════════════════════════════

class SeverityRequest(BaseModel):
    cpu:         float = Field(..., ge=0, le=100)
    memory:      float = Field(..., ge=0, le=100)
    disk:        float = Field(50.0, ge=0, le=100)
    latency:     float = Field(200.0, ge=0)
    error_count: int   = Field(..., ge=0)
    warn_count:  int   = Field(20, ge=0)
    alert_volume:int   = Field(3,  ge=0)
    duration_min:float = Field(30.0, ge=0)
    impacted_services: int = Field(1, ge=1)
    tower:   str = "Application"
    service: str = "api-gateway"

    model_config = {"json_schema_extra": {
        "example": {"cpu": 95, "memory": 88, "latency": 1200, "error_count": 230}
    }}


class SeverityResponse(BaseModel):
    severity:         str
    confidence:       float
    all_probabilities: Dict[str, float]


# ══════════════════════════════════════════════════════════════════
# Anomaly
# ══════════════════════════════════════════════════════════════════

class AnomalyRequest(BaseModel):
    cpu:          float = Field(..., ge=0, le=100)
    memory:       float = Field(..., ge=0, le=100)
    latency:      float = Field(..., ge=0)
    disk:         float = Field(50.0, ge=0, le=100)
    error_rate:   float = Field(0.5,  ge=0)
    net_in_mbps:  float = Field(100.0, ge=0)
    net_out_mbps: float = Field(80.0,  ge=0)
    request_rate: float = Field(500.0, ge=0)
    gc_pause_ms:  float = Field(20.0,  ge=0)
    thread_count: float = Field(50.0,  ge=0)
    tower: str = "Application"

    model_config = {"json_schema_extra": {
        "example": {"cpu": 95, "memory": 92, "latency": 8000, "error_rate": 25}
    }}


class AnomalyResponse(BaseModel):
    anomaly:   bool
    score:     float = Field(description="Normalised anomaly score [0, 1]")
    threshold: float
    raw_score: float


# ══════════════════════════════════════════════════════════════════
# Root Cause
# ══════════════════════════════════════════════════════════════════

class RootCauseRequest(BaseModel):
    cpu:         float = Field(..., ge=0, le=100)
    memory:      float = Field(..., ge=0, le=100)
    disk:        float = Field(50.0, ge=0, le=100)
    latency:     float = Field(200.0, ge=0)
    error_count: int   = Field(..., ge=0)
    warn_count:  int   = Field(20,   ge=0)
    alert_volume:int   = Field(3,    ge=0)
    duration_min:float = Field(30.0, ge=0)
    impacted_services: int = Field(1, ge=1)
    tower:   str = "Application"
    service: str = "api-gateway"

    model_config = {"json_schema_extra": {
        "example": {
            "cpu": 15, "memory": 20, "latency": 12000,
            "error_count": 800, "tower": "Database"
        }
    }}


class RootCauseCandidate(BaseModel):
    root_cause: str
    confidence: float


class RootCauseResponse(BaseModel):
    root_cause:        str
    confidence:        float
    top3:              List[RootCauseCandidate]
    all_probabilities: Dict[str, float]


# ══════════════════════════════════════════════════════════════════
# Investigate (full LangGraph workflow)
# ══════════════════════════════════════════════════════════════════

class InvestigateRequest(ObservabilityInput):
    incident_id: Optional[str] = None
    description: Optional[str] = Field(None, description="Free-text incident description")

    model_config = {"json_schema_extra": {
        "example": {
            "cpu_usage": 95, "memory_usage": 88,
            "disk_usage": 72, "error_count": 54,
            "description": "Intermittent 503 errors on order-service",
        }
    }}


class SimilarIncident(BaseModel):
    incident_id: str
    summary:     str
    root_cause:  str
    resolution:  str
    score:       float


class InvestigateResponse(BaseModel):
    incident_id:       str
    severity:          str
    severity_confidence: float
    anomaly:           bool
    anomaly_score:     float
    root_cause:        str
    root_cause_confidence: float
    similar_incidents: List[SimilarIncident]
    recommendations:   List[str]
    report:            str
    report_markdown:   str
    processing_time_ms: float


# ══════════════════════════════════════════════════════════════════
# Incidents DB
# ══════════════════════════════════════════════════════════════════

class IncidentRecord(BaseModel):
    incident_id:          str
    timestamp:            datetime
    severity:             str
    severity_confidence:  float
    anomaly:              bool
    anomaly_score:        float
    root_cause:           str
    root_cause_confidence:float
    tower:                str
    service:              str
    cpu_usage:            float
    memory_usage:         float
    disk_usage:           float
    error_count:          int
    report_summary:       Optional[str] = None


class IncidentListResponse(BaseModel):
    total:     int
    incidents: List[IncidentRecord]


# ══════════════════════════════════════════════════════════════════
# Health / root
# ══════════════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    status:    str
    version:   str
    models:    Dict[str, str]
    vector_db: str
    database:  str


class RootResponse(BaseModel):
    name:        str
    description: str
    version:     str
    docs_url:    str
