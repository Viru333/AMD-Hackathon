"""
Unified Agentic Observability and Root Cause Analysis Platform
FastAPI application entry point.

Run locally:
    cd backend
    uvicorn app:app --reload --port 8000

Or via the helper script:
    python app.py
"""
from __future__ import annotations
import logging
import sys
import os
import time

# ── ensure workspace root is on the path ─────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import router
from backend.config import API_PORT, API_HOST, API_VERSION, DEBUG
from backend.ml.inference import get_models
from backend.vector_store.qdrant_client import _get_client as init_qdrant
from backend.database.models import get_engine   # creates tables on first call

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("observability")


# ── Startup / shutdown ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  Unified Agentic Observability Platform — starting up")
    logger.info("=" * 60)

    # 1. Initialise DB (creates tables if needed)
    logger.info("Initialising database …")
    get_engine()
    logger.info("  Database ready")

    # 2. Load ML models
    get_models().load()

    # 3. Initialise Qdrant + seed knowledge base
    logger.info("Initialising Qdrant vector store …")
    init_qdrant()

    logger.info("=" * 60)
    logger.info("  🚀 Platform ready  |  docs: http://localhost:{}/docs".format(API_PORT))
    logger.info("=" * 60)

    yield

    logger.info("Shutting down …")


# ── FastAPI app ───────────────────────────────────────────────────

app = FastAPI(
    title       = "Unified Agentic Observability & RCA Platform",
    description = (
        "AI-powered backend for enterprise observability: "
        "anomaly detection, severity classification, root cause prediction, "
        "and LangGraph-driven automated RCA reports."
    ),
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    lifespan    = lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Request timing middleware ─────────────────────────────────────

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t0       = time.perf_counter()
    response = await call_next(request)
    elapsed  = round((time.perf_counter() - t0) * 1000, 1)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    return response

# ── Global error handler ─────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "path": str(request.url)},
    )

# ── Routes ───────────────────────────────────────────────────────

app.include_router(router, prefix=f"/api/{API_VERSION}")

# Keep root-level routes accessible without the version prefix
app.include_router(router)


# ── Dev server ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app:app",
        host    = API_HOST,
        port    = API_PORT,
        reload  = DEBUG,
        workers = 1,
    )
