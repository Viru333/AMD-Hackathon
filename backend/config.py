"""
Central configuration — override via environment variables.
"""
import os
from pathlib import Path

BASE_DIR   = Path(__file__).parent
ML_DIR     = BASE_DIR.parent/ "ml_project"  / "models"
DATA_DIR   = BASE_DIR.parent  / "data"

# ── ML model paths ────────────────────────────────────────────────
SEVERITY_MODEL_PATH  = str(ML_DIR / "severity_model.pkl")
ANOMALY_MODEL_PATH   = str(ML_DIR / "anomaly_model.pkl")
RCA_MODEL_PATH       = str(ML_DIR / "rca_model.pkl")
SCALER_SEVERITY_PATH = str(ML_DIR / "scaler_severity.pkl")
SCALER_ANOMALY_PATH  = str(ML_DIR / "scaler_anomaly.pkl")
SCALER_RCA_PATH      = str(ML_DIR / "scaler_rca.pkl")
SEV_LABEL_MAP_PATH   = str(ML_DIR / "severity_label_map.pkl")
RCA_LABEL_MAP_PATH   = str(ML_DIR / "rca_label_map.pkl")
ANOMALY_SCORE_PATH   = str(ML_DIR / "anomaly_score_params.pkl")

# ── Database ──────────────────────────────────────────────────────
# Use SQLite by default; honour DATABASE_URL only if it's a sqlite URL
# (Postgres requires psycopg2 which may not be installed locally)
_raw_db_url = os.getenv("DATABASE_URL", "")
if _raw_db_url.startswith("sqlite"):
    DATABASE_URL = _raw_db_url
else:
    DATABASE_URL = f"sqlite:///{BASE_DIR}/observability.db"

# ── Qdrant ────────────────────────────────────────────────────────
QDRANT_HOST       = os.getenv("QDRANT_HOST", ":memory:")   # use ":memory:" for local mode
QDRANT_PORT       = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = "incident_knowledge_base"
VECTOR_DIM        = 384        # all-MiniLM-L6-v2; change to 1024 for bge-m3

# ── Embeddings ────────────────────────────────────────────────────
# Set EMBEDDING_MODEL=BAAI/bge-m3 for full accuracy (needs ~2 GB RAM)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# ── API ───────────────────────────────────────────────────────────
API_HOST    = os.getenv("API_HOST", "0.0.0.0")
API_PORT    = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
API_VERSION = "v1"
DEBUG       = os.getenv("DEBUG", "false").lower() == "true"

# ── Report ────────────────────────────────────────────────────────
MAX_SIMILAR_INCIDENTS = 5
TOP_K_RUNBOOKS        = 3
