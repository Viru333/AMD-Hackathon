# Using the AMD-lab notebooks & ML models with this project

The AMD lab provides the GPUs (ROCm), the training **notebooks**, and the
**trained ML models**. This guide explains how to bring those assets into this
repo and make the platform agentic on AMD hardware.

There are three independent workloads. Only the last one strictly needs the GPU;
the first two benefit from ROCm but can run on CPU.

---

## 1. The classical ML models (severity / anomaly / root cause)

The repo already contains the inference code and artefacts:

- `backend/ml_code/severity_predictor.py`
- `backend/ml_code/anomaly_detector.py`
- `backend/ml_code/rootcause_predictor.py`
- trained artefacts in `ml_project/models/` (and `models.zip`)
- training data in `data/` (`X_*.csv`, `y_*.csv`)

**Mapping notebooks → repo:**

1. In the lab, your training notebooks end with something like
   `joblib.dump(model, "severity_xgb.pkl")`. Export every trained artefact.
2. Copy those `.pkl` / `.json` files into `ml_project/models/` (or unzip
   `models.zip`) so `backend/ml/inference.py` can load them.
3. Re-run a quick parity check: load each model and predict on a few rows of
   the matching `data/X_*.csv` and confirm the labels match the notebook.

> XGBoost has a ROCm/GPU build, but these tabular models are tiny — CPU
> inference is fine. Keep the GPU for the LLM (step 3).

If you only have notebooks (no exported artefacts), convert each training
notebook to a script and run it once to produce the artefacts:

```bash
jupyter nbconvert --to script train_severity.ipynb
python train_severity.py        # writes severity_xgb.pkl → ml_project/models/
```

---

## 2. Embeddings for the vector store (Qdrant)

`backend/vector_store/embeddings.py` uses `sentence-transformers`. On the AMD
lab this runs on the GPU automatically because `sentence-transformers` uses
PyTorch, and the **ROCm build of PyTorch** exposes the AMD GPU as a CUDA-like
device:

```bash
# inside a ROCm PyTorch environment in the lab
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# True  AMD Instinct MI...
```

No code change is required — PyTorch+ROCm transparently accelerates the
existing embedding code. Set `EMBEDDING_MODEL=BAAI/bge-m3` for higher accuracy
if the GPU memory allows.

---

## 3. The LLM (the agentic part) on vLLM + ROCm

This is what the AMD GPUs are really for. Take any instruct model from the lab
(or download one) and serve it with vLLM's ROCm build:

```bash
bash serve_vllm.sh            # see README — serves an OpenAI API on :8000
```

Then the agent in `rca_agent.py` calls it to generate the RCA narrative.

### Turning a lab notebook cell into the served agent

A typical lab notebook does inline generation:

```python
# notebook (single GPU, transformers)
from transformers import pipeline
pipe = pipeline("text-generation", model=MODEL, device=0)   # ROCm device
out = pipe(prompt, max_new_tokens=512)
```

vLLM replaces that with a **persistent, batched, high-throughput server**, so
many investigations can be served concurrently. The migration is:

| Notebook (transformers) | This repo (vLLM) |
|-------------------------|------------------|
| `pipeline("text-generation", device=0)` | `serve_vllm.sh` once |
| `pipe(prompt)` in the cell | `rca_agent.generate_rca_report(evidence)` |
| manual prompt string | structured `SYSTEM_PROMPT` + evidence JSON |

### End-to-end agentic flow on the lab

```
1. (CPU/GPU) backend ML models  → severity, anomaly, root_cause
2. (GPU/ROCm) sentence-transformers → embeddings → Qdrant similar incidents
3. (GPU/ROCm) vLLM-served LLM   → reasons over 1+2 → RCA report
```

Wire step 3 into the existing LangGraph by swapping in `agentic_report_node`
(see README "Make the existing pipeline agentic").

---

## Quick checklist for the lab

- [ ] `rocm-smi` shows the assigned GPU(s)
- [ ] ROCm PyTorch: `torch.cuda.is_available()` is `True`
- [ ] Trained ML artefacts copied into `ml_project/models/`
- [ ] `bash serve_vllm.sh` serves `http://<host>:8000/v1`
- [ ] `python -m agentic_rocm_vllm.run_demo` prints an LLM report
- [ ] (optional) `agentic_report_node` registered in `backend/graph/workflow.py`
