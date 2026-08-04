# Enterprise Model Registry Documentation

This document describes the registered models parameters tracking, quantization setups, and active default models selection workflows.

---

## 🖥️ Local Model Registry Setup

The registry maps local models running via Ollama to database parameters logs:
- **llama3:8b**: Standard default model, optimized with `Q4_K_M` quantization.
- **qwen2:7b**: Deep reasoning model, featuring a `32,768` token context size.
- **mistral:7b**: Balanced local performance engine.
- **phi3:mini**: Lightweight offline execution model.

---

## ⚙️ Model Activation Workflow

- Only **one model** can be designated as the active system default.
- Toggling a model's activation sets its status to `"active"` and sets all other models to `"inactive"`.
- Activations are recorded in the Prometheus gauge metrics `model_changes_total`.
