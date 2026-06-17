# Agentic RCA on AMD ROCm + vLLM (optional layer)

This folder makes the observability platform **agentic** by running an LLM
locally on **AMD GPUs (ROCm)** through **vLLM**, and using it to reason over
the ML model outputs to write the root-cause-analysis (RCA) report.

> ⚠️ This folder is **fully optional and self-contained**. Nothing in
> `backend/` or `frontend/` imports it, so adding it cannot break the existing
> application. You opt in either by running the standalone demo or by wiring
> the drop-in LangGraph node (see below).

---

## Why this exists

Today `backend/reports/report_generator.py` builds the RCA report from **fixed
templates**. That is deterministic but not "agentic" — it doesn't *reason*.

The hackathon goal was to make the use case agentic using **ROCm + vLLM**. This
layer does exactly that: it feeds the structured ML outputs (severity, anomaly,
root cause), the retrieved similar incidents and the runbook hints into an LLM
hosted on an AMD GPU, and asks it to produce the narrative, the justification
and the remediation plan.

```
 ML models (XGBoost/IsolationForest/…)         Qdrant retrieval + runbooks
            │                                            │
            └──────────────► evidence dict ◄─────────────┘
                                  │
                       rca_agent.generate_rca_report()
                                  │  (OpenAI-compatible HTTP)
                                  ▼
                vLLM OpenAI server  ──runs on──►  AMD GPU (ROCm)
                                  │
                                  ▼
                       Markdown RCA report
```

---

## Files

| File | Purpose |
|------|---------|
| `serve_vllm.sh` | Launches the vLLM OpenAI server on an AMD GPU (run **inside the AMD lab**). |
| `vllm_client.py` | Talks to the vLLM server (OpenAI SDK, with an httpx fallback). |
| `rca_agent.py` | Builds the prompt, calls the LLM, returns the RCA report. Also exposes `agentic_report_node` — a **drop-in** LangGraph node. |
| `config.py` | All settings via environment variables. |
| `run_demo.py` | Standalone end-to-end demo with sample evidence. |
| `requirements.txt` | Client deps; server (vLLM/ROCm) install notes. |
| `notebooks_integration.md` | **How to use the AMD-lab notebooks & models here.** |

---

## How to use the AMD lab

The AMD lab gives you (a) AMD GPUs with **ROCm**, and (b) the notebooks +
trained ML models. The plan to utilise it:

### 1. Serve a model with vLLM on ROCm (in the lab)

Use AMD's prebuilt ROCm vLLM image (do **not** install the CUDA wheel):

```bash
docker run -it --device=/dev/kfd --device=/dev/dri --group-add video \
  --shm-size 16G -p 8000:8000 rocm/vllm bash

# inside the container:
bash serve_vllm.sh        # serves http://0.0.0.0:8000/v1
```

`serve_vllm.sh` checks `rocm-smi`, sets `HIP_VISIBLE_DEVICES`, and starts
`vllm.entrypoints.openai.api_server`. Pick any instruct model the lab GPUs can
hold (e.g. `meta-llama/Llama-3.1-8B-Instruct`, or a smaller one for a single
GPU) via the `VLLM_MODEL` env var.

### 2. Point the agent at the server

```bash
export VLLM_BASE_URL=http://<lab-gpu-host>:8000/v1
export VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
pip install -r agentic_rocm_vllm/requirements.txt
python -m agentic_rocm_vllm.run_demo
```

You'll get an LLM-generated RCA report. If the server is down and
`VLLM_FALLBACK_ON_ERROR=true` (default), you get a template report instead so
the wiring is still verifiable offline.

### 3. (Optional) Make the existing pipeline agentic

Without editing any backend file, register the drop-in node:

```python
from agentic_rocm_vllm.rca_agent import agentic_report_node
# in backend/graph/workflow.py _build_graph(), swap:
builder.add_node("report", agentic_report_node)
```

It reads/writes the same `state` keys the current graph already uses
(`severity`, `anomaly`, `root_cause`, `similar_incidents`, `runbooks`,
`report`), so it slots in cleanly.

---

## Using the lab's notebooks & ML models

See **[notebooks_integration.md](./notebooks_integration.md)** for the full
walkthrough of taking the trained models / notebooks from the AMD lab and
serving their predictions, plus running the embeddings + LLM on ROCm.

---

## Environment variables

| Var | Default | Meaning |
|-----|---------|---------|
| `VLLM_BASE_URL` | `http://localhost:8000/v1` | vLLM OpenAI endpoint |
| `VLLM_MODEL` | `meta-llama/Llama-3.1-8B-Instruct` | served model id |
| `VLLM_API_KEY` | `EMPTY` | any non-empty value if auth is off |
| `VLLM_MAX_TOKENS` | `1024` | max generated tokens |
| `VLLM_TEMPERATURE` | `0.2` | sampling temperature |
| `VLLM_FALLBACK_ON_ERROR` | `true` | template fallback if server down |
