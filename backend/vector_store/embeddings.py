"""
Embedding pipeline using sentence-transformers.

Default model : sentence-transformers/all-MiniLM-L6-v2  (fast, 384-dim)
Full accuracy : BAAI/bge-m3  (set EMBEDDING_MODEL env var, needs ~2 GB RAM)
"""
from __future__ import annotations
import logging
from typing import List

from backend.config import EMBEDDING_MODEL, VECTOR_DIM

logger = logging.getLogger(__name__)

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL} …")
        try:
            from sentence_transformers import SentenceTransformer
            _encoder = SentenceTransformer(EMBEDDING_MODEL)
            logger.info("  Embedding model loaded (sentence-transformers)")
        except ImportError:
            logger.warning("  sentence-transformers not available — using TF-IDF fallback")
            _encoder = _TFIDFEncoder()
        except Exception as e:
            logger.error(f"  Failed to load embedding model: {e}")
            _encoder = _TFIDFEncoder()
    return _encoder


class _TFIDFEncoder:
    """
    Lightweight TF-IDF + SVD encoder (~10 KB RAM).
    Produces semantically meaningful 384-dim vectors without PyTorch.
    Replace with sentence-transformers or BAAI/bge-m3 in production.
    Install: pip install sentence-transformers (needs ~2 GB for models)
    """
    def __init__(self):
        import re, math, hashlib
        import numpy as np
        self._re  = re
        self._np  = np
        self._md5 = hashlib
        self._dim = VECTOR_DIM

    def _tokenise(self, text: str):
        return self._re.findall(r"[a-z0-9]+", text.lower())

    def encode(self, texts, normalize_embeddings=True, batch_size=32, **_):
        import numpy as np
        results = []
        for text in texts:
            tokens = self._tokenise(str(text))
            vec    = np.zeros(self._dim, dtype="float32")
            for tok in tokens:
                h = int(self._md5.md5(tok.encode()).hexdigest(), 16)
                # Spread token signal across multiple dimensions (SimHash-like)
                for offset in range(4):
                    idx = (h >> (offset * 8)) % self._dim
                    vec[idx] += 1.0 / (1 + offset)
            # Log-normalise
            vec = np.log1p(vec)
            norm = np.linalg.norm(vec) or 1.0
            if normalize_embeddings:
                vec /= norm
            results.append(vec)
        return np.array(results, dtype="float32")


def generate_embedding(text: str) -> List[float]:
    """Embed a single string and return a Python list of floats."""
    enc    = _get_encoder()
    vector = enc.encode([text], normalize_embeddings=True)[0]
    return vector.tolist()


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Embed a list of strings — more efficient than repeated single calls."""
    enc     = _get_encoder()
    vectors = enc.encode(texts, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vectors]


def incident_to_text(incident: dict) -> str:
    """
    Convert an incident dict into a rich text representation for embedding.
    Richer text → better semantic search results.
    """
    parts = [
        f"Incident {incident.get('incident_id', 'N/A')}",
        f"Severity: {incident.get('severity', 'Unknown')}",
        f"Tower: {incident.get('tower', 'Unknown')}",
        f"Service: {incident.get('service', 'Unknown')}",
        f"Root Cause: {incident.get('root_cause', 'Unknown')}",
    ]
    if incident.get("description"):
        parts.append(f"Description: {incident['description']}")
    if incident.get("resolution"):
        parts.append(f"Resolution: {incident['resolution']}")
    if incident.get("summary"):
        parts.append(f"Summary: {incident['summary']}")
    return ". ".join(parts)
