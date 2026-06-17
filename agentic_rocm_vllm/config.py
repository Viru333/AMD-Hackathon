"""
Configuration for the (optional) ROCm + vLLM agentic layer.

This module is fully self-contained and is NOT imported anywhere by the
existing backend, so dropping this folder into the repo cannot affect the
running application. Everything is driven by environment variables so the
same code runs against:

  * a local vLLM server on an AMD GPU (ROCm) in the AMD lab, or
  * any OpenAI-compatible endpoint for local development.
"""
from __future__ import annotations
import os

# Base URL of the OpenAI-compatible server exposed by vLLM.
# vLLM's OpenAI server defaults to http://<host>:8000/v1
VLLM_BASE_URL: str = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")

# Model id as registered with vLLM (the --served-model-name you launch with).
VLLM_MODEL: str = os.getenv("VLLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")

# vLLM accepts any non-empty key when auth is not configured.
VLLM_API_KEY: str = os.getenv("VLLM_API_KEY", "EMPTY")

# Generation controls.
MAX_TOKENS: int = int(os.getenv("VLLM_MAX_TOKENS", "1024"))
TEMPERATURE: float = float(os.getenv("VLLM_TEMPERATURE", "0.2"))
REQUEST_TIMEOUT_S: float = float(os.getenv("VLLM_TIMEOUT_S", "60"))

# When true, the agent degrades gracefully to a template report if the
# vLLM server is unreachable instead of raising. Keeps demos resilient.
FALLBACK_ON_ERROR: bool = os.getenv("VLLM_FALLBACK_ON_ERROR", "true").lower() == "true"
