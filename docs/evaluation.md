# Enterprise AI Evaluation Engine Documentation

This document outlines the metrics, scoring formulas, A/B models side-by-side comparisons, and batch benchmark progression logging.

---

## ⚖️ Evaluation Scoring Formula

Evaluation scores (0-100) are computed using a weighted metrics breakdown:

| Evaluation Metric | Weight | Calculation Basis |
| :--- | :---: | :--- |
| **Answer Relevance** | 30% | Based on text length and keyword density checks. |
| **SQL Correctness** | 30% | `100.0` if valid select query structure; `0.0` otherwise. |
| **Citation Coverage** | 20% | `100.0` if citations are matched; `0.0` if empty. |
| **Latency Penalty** | 20% | Penalized linearly if duration exceeds `3000ms`. |

---

## ⚖️ A/B Model Comparison

The side-by-side comparison engine:
- Concurrently triggers execution of the same prompt on model A and model B.
- Records responses, latencies, citations count, and rates overall scores independently.
- Displays metrics comparison panels in the front-end layout.
