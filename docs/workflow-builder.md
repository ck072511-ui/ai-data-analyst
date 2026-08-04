# Visual AI Workflow Builder UI

This document provides details on configuring visual nodes, templates, scheduling, and live monitoring.

## Interface Panels

The workspace is organized into three main sub-tabs:

### 1. Builder Canvas

- **Nodes Library**: Drag-and-drop catalog panel to add steps.
- **Canvas Board**: Drag-and-drop workflow dashboard displaying the active DAG.
- **Configuration Panel**: Responsive editor sidebar allowing parameters config, input source binding, and custom retry/timeout limits.

### 2. Live Executions & Logs

- **Timelines Monitor**: Shows active node durations, progress logs, and retry occurrences.
- **Diagnostics Console**: Terminal panel presenting runtime console messages returned from backend executors.

### 3. Pipeline Templates

Allows loading pre-packaged configurations:
- **Sales Analytics**: Auto-inspects revenue metrics, runs SQL aggregates, and builds PDF logs.
- **Customer Churn Tracker**: Cleans nulls, runs multi-agent correlation plans, and fires warnings.
- **Financial Audit Insights**: Audits database ledger entries and drafts editable Word audit reports.
- **Data Quality Audit**: Profiles datasets for formats correctness.
- **Executive Reporting**: Generates PowerPoint slide presentations.
- **AI Insights Pipeline**: Grounding RAG queries on clean datasets.

## Variables and Parameter Binding

Nodes communicate by binding output fields (e.g. `dataset_id`) as inputs to subsequent steps. The builder tracks connections to build the topological graph layout.

## Automatic Recurrence Schedules

Schedules are configured via the builder footer:
- **Manual**: Direct manual execution.
- **One-time**: Runs at a scheduled timestamp.
- **Daily/Weekly/Monthly**: Standard recurrence cycles.
- **Cron**: Parses complex crons (e.g., `0 9 * * 1-5` for weekdays at 9 AM).
