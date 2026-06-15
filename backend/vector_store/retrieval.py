"""
High-level retrieval functions used by the LangGraph nodes.
"""
from __future__ import annotations
from typing import Any, Dict, List

from backend.vector_store.embeddings import generate_embedding, incident_to_text
from backend.vector_store.qdrant_client import insert_document, search_similar_incidents
from backend.config import MAX_SIMILAR_INCIDENTS, TOP_K_RUNBOOKS


def retrieve_similar_incidents(
    incident: Dict[str, Any],
    top_k: int = MAX_SIMILAR_INCIDENTS,
) -> List[Dict[str, Any]]:
    """
    Embed an incident and return the most similar historical incidents
    from the knowledge base.
    """
    text      = incident_to_text(incident)
    embedding = generate_embedding(text)
    return search_similar_incidents(embedding, top_k=top_k)


def store_incident(incident: Dict[str, Any]) -> bool:
    """
    Embed and store a new incident in the knowledge base after investigation.
    """
    text      = incident_to_text(incident)
    embedding = generate_embedding(text)
    return insert_document(
        incident_id=incident.get("incident_id", "UNKNOWN"),
        summary=incident.get("summary", incident_to_text(incident)[:200]),
        root_cause=incident.get("root_cause", "Unknown"),
        resolution=incident.get("resolution", ""),
        embedding=embedding,
        extra_payload={
            "severity": incident.get("severity", ""),
            "tower":    incident.get("tower", ""),
            "service":  incident.get("service", ""),
        },
    )


RUNBOOK_DB: Dict[str, List[str]] = {
    "Database Failure": [
        "Check DB connection pool metrics — look for `max_connections` exhaustion",
        "Run `SHOW PROCESSLIST` (MySQL) / `SELECT * FROM pg_stat_activity` (Postgres)",
        "Verify replication lag: `SHOW SLAVE STATUS` or `pg_stat_replication`",
        "Kill blocking long-running queries",
        "Consider read-replica failover if primary is unresponsive",
        "Restore from latest backup if data corruption is confirmed",
    ],
    "Network Failure": [
        "Run `ping` and `traceroute` to isolate the failing hop",
        "Check BGP session status on core routers",
        "Inspect firewall ACL change log for recent modifications",
        "Capture packets with `tcpdump` on suspected interface",
        "Failover to backup network link / secondary AZ",
        "Notify ISP/cloud provider if external link is affected",
    ],
    "Memory Leak": [
        "Capture heap dump: `kill -3 <pid>` (JVM) or `py-spy dump` (Python)",
        "Check GC logs for increasing old-gen occupancy",
        "Identify top memory consumers: `jmap -histo <pid>`",
        "Rolling restart of affected pods to restore service",
        "Increase JVM heap limit as temporary measure: `-Xmx`",
        "Profile with async-profiler / memory-profiler to find leak source",
    ],
    "CPU Saturation": [
        "Identify top CPU consumers: `top -c` or `kubectl top pods`",
        "Check for runaway batch jobs or infinite loops",
        "Scale out horizontally: add replicas or increase autoscaling max",
        "Add CPU limits in Kubernetes PodSpec to prevent resource hogging",
        "Throttle low-priority batch workloads during peak hours",
        "Review recent code deployments for O(n²) algorithm regressions",
    ],
    "Disk Failure": [
        "Check SMART data: `smartctl -a /dev/sdX`",
        "Inspect kernel dmesg for I/O errors",
        "Verify RAID health: `cat /proc/mdstat`",
        "Replace failed disk and rebuild RAID array",
        "Restore data from backup if filesystem corruption detected",
        "Expand disk capacity or add a new volume to prevent future saturation",
    ],
    "Service Crash": [
        "Inspect application logs for the last ERROR before crash",
        "Check exit code — 137 = OOM kill, 1 = unhandled exception",
        "Redeploy the previous stable release tag",
        "Enable circuit breaker for downstream dependency calls",
        "Add liveness/readiness probes in Kubernetes",
        "Review dependency health (DB, cache, message broker) before redeploy",
    ],
    "Kubernetes Pod Failure": [
        "Run `kubectl describe pod <name>` to inspect events",
        "Check `kubectl logs <name> --previous` for last crash output",
        "Verify resource requests/limits — look for OOMKilled",
        "Inspect image pull status for registry connectivity",
        "Roll back to previous stable Deployment revision",
        "Review PodDisruptionBudget and node capacity",
    ],
    "Cloud Resource Exhaustion": [
        "Check service quotas in cloud console (vCPU, IPs, EBS, subnets)",
        "Request quota increase via support ticket",
        "Release unused reserved instances or idle volumes",
        "Enable auto-scaling with appropriate max capacity",
        "Review resource tagging to identify orphaned resources",
        "Consider multi-region failover if quota cannot be increased quickly",
    ],
}


def get_runbooks(root_cause: str, top_k: int = TOP_K_RUNBOOKS) -> List[str]:
    """Return actionable runbook steps for a given root cause."""
    steps = RUNBOOK_DB.get(root_cause, [
        "Review recent changes in the affected service",
        "Check infrastructure metrics (CPU, memory, disk, network)",
        "Escalate to on-call engineer with full observability data",
    ])
    return steps[:top_k]
