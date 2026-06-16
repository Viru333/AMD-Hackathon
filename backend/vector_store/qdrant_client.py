"""
Qdrant vector store client.

Runs in-memory by default (QDRANT_HOST=:memory:).
Point QDRANT_HOST to a real Qdrant server for production.
"""
from __future__ import annotations
import logging
import uuid
from typing import Any, Dict, List, Optional

from backend.config import (
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION, VECTOR_DIM,
)

logger = logging.getLogger(__name__)

_client = None
_collection_ready = False


def _get_client():
    global _client, _collection_ready
    if _client is not None:
        return _client

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        if QDRANT_HOST == ":memory:":
            logger.info("Starting Qdrant in-memory …")
            _client = QdrantClient(":memory:")
        else:
            logger.info(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT} …")
            _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Create collection if it doesn't exist
        existing = [c.name for c in _client.get_collections().collections]
        if QDRANT_COLLECTION not in existing:
            _client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(
                    size=VECTOR_DIM,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"  Qdrant collection '{QDRANT_COLLECTION}' created")
            _collection_ready = True
            _seed_knowledge_base(_client)
        else:
            _collection_ready = True
            logger.info(f"  Qdrant collection '{QDRANT_COLLECTION}' ready")

    except Exception as e:
        logger.error(f"  Qdrant unavailable: {e}")
        _client = _FallbackVectorStore()

    return _client


# ── Document operations ───────────────────────────────────────────

def insert_document(
    incident_id: str,
    summary: str,
    root_cause: str,
    resolution: str,
    embedding: List[float],
    extra_payload: Optional[Dict[str, Any]] = None,
) -> bool:
    """Upsert a document into the vector store."""
    client = _get_client()
    try:
        from qdrant_client.models import PointStruct
        payload = {
            "incident_id": incident_id,
            "summary":     summary,
            "root_cause":  root_cause,
            "resolution":  resolution,
        }
        if extra_payload:
            payload.update(extra_payload)

        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, incident_id))
        # Convert uuid to int for qdrant (it accepts both str and int)
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[PointStruct(
                id=abs(hash(incident_id)) % (2**31),
                vector=embedding,
                payload=payload,
            )],
        )
        return True
    except Exception as e:
        logger.error(f"insert_document error: {e}")
        return False


def search_similar_incidents(
    query_embedding: List[float],
    top_k: int = 5,
    score_threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    """Return top-k similar incidents from the vector store."""
    client = _get_client()
    try:
        # qdrant-client >= 1.9 uses query_points(); fallback to legacy search()
        if hasattr(client, "query_points"):
            result = client.query_points(
                collection_name=QDRANT_COLLECTION,
                query=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
            )
            hits = result.points
        else:
            hits = client.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
            )
        return [
            {
                "incident_id": h.payload.get("incident_id", "UNKNOWN"),
                "summary":     h.payload.get("summary", ""),
                "root_cause":  h.payload.get("root_cause", ""),
                "resolution":  h.payload.get("resolution", ""),
                "score":       round(float(h.score), 4),
            }
            for h in hits
        ]
    except Exception as e:
        logger.error(f"search_similar_incidents error: {e}")
        return []


def get_collection_info() -> Dict[str, Any]:
    client = _get_client()
    try:
        info = client.get_collection(QDRANT_COLLECTION)
        return {
            "status": "ready",
            "vectors_count": getattr(info, "points_count", None) or getattr(info, "vectors_count", None) or 0,
            "collection": QDRANT_COLLECTION,
        }
    except Exception:
        return {"status": "unavailable", "vectors_count": 0, "collection": QDRANT_COLLECTION}


# ── Seed knowledge base ───────────────────────────────────────────

def _seed_knowledge_base(client) -> None:
    """Pre-populate the vector store with realistic incident runbooks."""
    from backend.vector_store.embeddings import generate_embedding

    SEED_INCIDENTS = [
        {
            "incident_id": "INC-000001",
            "summary":     "Database connection pool exhausted; all queries timing out",
            "root_cause":  "Database Failure",
            "resolution":  "Increase max_connections; restart connection pool; add read replicas",
            "tower":       "Database",
        },
        {
            "incident_id": "INC-000002",
            "summary":     "BGP route flap caused 15-minute network partition across AZ-2",
            "root_cause":  "Network Failure",
            "resolution":  "Restore BGP sessions; failover traffic to AZ-1; update route filters",
            "tower":       "Network",
        },
        {
            "incident_id": "INC-000003",
            "summary":     "JVM heap exhausted on payment-gateway; OOM killer terminated process",
            "root_cause":  "Memory Leak",
            "resolution":  "Rolling restart; increase -Xmx; add heap dump on OOM; profile with async-profiler",
            "tower":       "Application",
        },
        {
            "incident_id": "INC-000004",
            "summary":     "Runaway batch job saturated all vCPUs for 40 minutes",
            "root_cause":  "CPU Saturation",
            "resolution":  "Kill batch job; add CPU limits in K8s; implement job scheduling throttle",
            "tower":       "Compute",
        },
        {
            "incident_id": "INC-000005",
            "summary":     "RAID-5 disk failure caused I/O errors on /var/lib/postgresql",
            "root_cause":  "Disk Failure",
            "resolution":  "Replace failed disk; rebuild RAID array; restore from backup if data loss",
            "tower":       "Storage",
        },
        {
            "incident_id": "INC-000006",
            "summary":     "order-service crashed due to unhandled NullPointerException in payment flow",
            "root_cause":  "Service Crash",
            "resolution":  "Redeploy v2.3.1 hotfix; add null checks; enable circuit breaker",
            "tower":       "Application",
        },
        {
            "incident_id": "INC-000007",
            "summary":     "auth-service pod CrashLoopBackOff after config-map change",
            "root_cause":  "Kubernetes Pod Failure",
            "resolution":  "Rollback configmap; fix YAML syntax; check pod resource limits",
            "tower":       "Cloud",
        },
        {
            "incident_id": "INC-000008",
            "summary":     "AWS vCPU quota exhausted; auto-scaling group could not launch new instances",
            "root_cause":  "Cloud Resource Exhaustion",
            "resolution":  "Request quota increase via AWS console; release unused reserved instances",
            "tower":       "Cloud",
        },
        {
            "incident_id": "INC-000009",
            "summary":     "Slow queries on orders table after index dropped by migration script",
            "root_cause":  "Database Failure",
            "resolution":  "Re-create missing index; kill long-running queries; add query timeout",
            "tower":       "Database",
        },
        {
            "incident_id": "INC-000010",
            "summary":     "Network packet loss 30% caused by misconfigured firewall ACL",
            "root_cause":  "Network Failure",
            "resolution":  "Revert ACL change; test with packet capture; notify network team",
            "tower":       "Network",
        },
        {
            "incident_id": "INC-000011",
            "summary":     "analytics-engine OOM after unbounded cache growth with no eviction policy",
            "root_cause":  "Memory Leak",
            "resolution":  "Set cache max-size; add LRU eviction; monitor heap weekly",
            "tower":       "Application",
        },
        {
            "incident_id": "INC-000012",
            "summary":     "Kubernetes node pressure evicted 12 pods; PVC mount failures followed",
            "root_cause":  "Kubernetes Pod Failure",
            "resolution":  "Add node capacity; implement PodDisruptionBudget; review eviction thresholds",
            "tower":       "Cloud",
        },
    ]

    logger.info(f"  Seeding {len(SEED_INCIDENTS)} knowledge-base documents …")
    for doc in SEED_INCIDENTS:
        text      = f"{doc['summary']} Root cause: {doc['root_cause']}. Resolution: {doc['resolution']}"
        embedding = generate_embedding(text)
        insert_document(
            incident_id=doc["incident_id"],
            summary=doc["summary"],
            root_cause=doc["root_cause"],
            resolution=doc["resolution"],
            embedding=embedding,
            extra_payload={"tower": doc.get("tower", "")},
        )
    logger.info("  Knowledge base seeded")


# ── Fallback (no qdrant installed) ───────────────────────────────

class _FallbackVectorStore:
    """In-process brute-force cosine similarity when Qdrant is unavailable."""

    def __init__(self):
        self._docs: list[dict] = []

    def upsert(self, collection_name, points):
        for p in points:
            self._docs.append({"vector": p.vector, "payload": p.payload, "id": p.id})

    def _cosine_hits(self, query_vector, limit, score_threshold):
        import numpy as np

        class _Hit:
            def __init__(self, payload, score):
                self.payload = payload
                self.score   = score

        if not self._docs:
            return []
        q = np.array(query_vector, dtype="float32")
        q /= np.linalg.norm(q) + 1e-9
        scored = []
        for doc in self._docs:
            v = np.array(doc["vector"], dtype="float32")
            v /= np.linalg.norm(v) + 1e-9
            scored.append(_Hit(doc["payload"], float(np.dot(q, v))))
        scored.sort(key=lambda x: -x.score)
        return [h for h in scored[:limit] if h.score >= score_threshold]

    def search(self, collection_name, query_vector, limit=5, score_threshold=0.0):
        return self._cosine_hits(query_vector, limit, score_threshold)

    def query_points(self, collection_name, query, limit=5, score_threshold=0.0, **_):
        hits = self._cosine_hits(query, limit, score_threshold)

        class _Result:
            def __init__(self, points):
                self.points = points
        return _Result(hits)

    def get_collections(self):
        class _R:
            collections = []
        return _R()

    def create_collection(self, **_): pass

    def get_collection(self, name):
        docs = self._docs

        class _I:
            vectors_count = len(docs)
        return _I()
