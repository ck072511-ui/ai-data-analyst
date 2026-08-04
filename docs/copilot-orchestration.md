# Copilot Action Orchestration & Visual Workflows

This document explains the multi-step execution sequencing and the automated translation of chat logs into visual workflow DAG configurations.

## 1. Action Orchestration Pipeline

When a user submits a query containing multiple operational requests:
> *"Analyze our sales, clean columns formatting issues, execute query totals, and export a PDF report."*

The Copilot Sequences these actions inside the Orchestrator according to a strict execution hierarchy:

```
[Start Input] 
      │
      ▼
1. Dataset Ingestion / Analysis ──► Generates quality report scorecards
      │
      ▼
2. AI Quality Cleaning Imputation ──► Resolves nulls & formatting errors
      │
      ▼
3. Analytics SQL Translation ──► Formulates queries and fetches rows
      │
      ▼
4. Program Explainability (XAI) ──► Computes query plan security audits
      │
      ▼
5. Report Document Generation ──► Compiles findings into PDF / Word formats
      │
      ▼
[End Output Response]
```

---

## 2. Visual Workflow Code Generation

Users can convert their current conversation thread into a reusable visual workflow DAG by prompting:
> *"Create a workflow from this conversation."*

The visual generator executes the following compiler logic:
1. **Intents Audit**: Analyzes past conversation messages to identify triggered capabilities (`Data Cleaning`, `SQL Analytics`, etc.).
2. **DAG Compilation**: Builds a standard node-edge graph configuration:
   - **Start Node**: `notification` alert verifying execution initiation.
   - **Operations Nodes**: Sequential blocks mapping to triggered intents (e.g. `data_profiling` -> `data_cleaning` -> `sql_query` -> `report_generation`).
   - **Edges**: Connection paths linking targets sequentially.
3. **Database Injection**: Saves a new record to the `Workflow` database table containing the JSON DAG string, allowing it to load inside the visual workflow Builder workspace instantly.

---

## 3. Orchestrator Telemetry Metrics

Prometheus statistics are collected on each chat orchestration run:
- **Orchestration duration**: Measured and observed under histogram metrics.
- **Failures tracker**: Failed steps increment error thresholds.
- **Intent counters**: Logs distribution of invoked capabilities.
