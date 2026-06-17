#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Launch a vLLM OpenAI-compatible server on an AMD GPU (ROCm).
#
# Run this INSIDE the AMD lab (where ROCm + the GPU are available).
# It serves a model over http://0.0.0.0:8000/v1 which rca_agent.py talks to.
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

MODEL="${VLLM_MODEL:-meta-llama/Llama-3.1-8B-Instruct}"
PORT="${VLLM_PORT:-8000}"
SERVED_NAME="${VLLM_SERVED_NAME:-$MODEL}"

# Confirm ROCm sees the AMD GPU(s).
echo "── ROCm devices ──────────────────────────────"
rocm-smi --showproductname || echo "WARN: rocm-smi not found — are you inside the ROCm container?"
echo

# vLLM has first-class ROCm support. In the AMD lab use the prebuilt ROCm
# image (e.g. rocm/vllm) or a wheel built for ROCm; do NOT install the CUDA wheel.
#   docker run -it --device=/dev/kfd --device=/dev/dri --group-add video \
#     -p ${PORT}:${PORT} rocm/vllm bash
#
# HIP/ROCm visibility (adjust to the GPUs assigned to you):
export HIP_VISIBLE_DEVICES="${HIP_VISIBLE_DEVICES:-0}"

echo "── Starting vLLM ─────────────────────────────"
echo "model=${MODEL}  port=${PORT}  HIP_VISIBLE_DEVICES=${HIP_VISIBLE_DEVICES}"

exec python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL}" \
  --served-model-name "${SERVED_NAME}" \
  --port "${PORT}" \
  --dtype float16 \
  --gpu-memory-utilization "${VLLM_GPU_MEM_UTIL:-0.90}" \
  --max-model-len "${VLLM_MAX_MODEL_LEN:-8192}"
