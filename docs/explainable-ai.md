# Enterprise Explainable AI (XAI) & Confidence Engine Documentation

This guide describes the explainability parsing architecture, the weighted confidence scoring formula, trace evidence compilation logs, enterprise auditing workflows, and system constraints.

---

## 📐 Explainability Architecture

The XAI Engine programmatically structures explanation payloads without exposing raw Chain-of-Thought (CoT) strings:

```mermaid
graph TD
    A[React Client / ExplainabilityDashboard] -->|GET /explain/{execution_id}| B[FastAPI routes/xai]
    B -->|Fetch Execution logs| C[SQLite db / agent_executions]
    C -->|Shared Memory & Timeline payload| B
    
    B -->|Calculate Confidence Weights| D[ConfidenceService]
    B -->|Parse SQL structures| E[XAIService.parse_sql_explanation]
    B -->|Aggregate document citations| F[XAIService.parse_rag_explanation]
    B -->|Summarize agent logs| G[XAIService.parse_agent_explanation]
    
    E -->|Extract Tables / Columns / Complexities| H[SQL explanation JSON]
    F -->|Count unique files & warnings| I[RAG explanation JSON]
    G -->|Extract Planner Tasks & Critic check status| J[Agent explanation JSON]
    
    H & I & J & D -->|Build consolidated XAI report| K[REST Response]
    K -->|Render grids drawers| A
```

---

## ⚖️ Confidence Engine Formula

The system computes confidence scores (0-100) using a weighted parameter mapping:

| Metric Indicator | Weight | Calculation Basis |
| :--- | :---: | :--- |
| **SQL Validation** | 25% | `100.0` if SQL ran without error; `0.0` otherwise. |
| **Schema Match** | 20% | `100.0` if database schema references mapped successfully. |
| **Citation Coverage** | 20% | `95.0` if documents cited; `80.0` if business glossaries matched. |
| **Agent Agreement** | 20% | Success ratio of completed tasks inside the timeline logs. |
| **Data Completeness** | 15% | `100.0` if output rows returned; `50.0` if query was empty. |

### Classification Levels
- **High Confidence**: Score $\ge 80.0\%$
- **Medium Confidence**: Score $\ge 50.0\%$
- **Low Confidence**: Score $< 50.0\%$

---

## 🔍 Evidence Generation & Audit Workflow

For compliance audits, the engine generates:
1. **Uncertainty Warnings**: Warns users if RAG citations are empty (`Warning: No document sources were cited to ground this answer.`).
2. **Deterministic SQL Explanations**: Identifies referenced tables, filters, joins, and aggregates directly using regex parsers on the executed queries.
3. **Critic Audits**: Summarizes Critic validations, potential inconsistencies, and recovery loops count.

---

## ⚠️ Known Limitations

1. **Static SQL Parser**: Parsing SQL queries using regex handles SELECT queries safely. Complex nested subqueries might occasionally map to a generic "Medium" complexity rating.
2. **Citation Relevance**: Citation scores measure source document matches. The accuracy of the documents themselves is assumed.
