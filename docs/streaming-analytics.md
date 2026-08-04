# Real-Time Analytics and Alert Engine

This document details the windowing mechanisms, anomaly detection math, alert routing, and workflow triggers configured in the Real-Time Streaming Analytics Engine.

## Windowing Models

The engine supports three partition styles:

1. **Tumbling Windows**: Non-overlapping time windows of fixed length. Once the duration elapsed, all collected events are aggregated, and a new window begins.
2. **Sliding Windows**: Overlapping time windows. A new window of fixed size begins every `slide_sec` seconds, resulting in concurrent active windows processing overlapping events.
3. **Session Windows**: Gap-based windows. Closes if no new event arrives within the configured inactivity gap.

### Aggregate Operators

Window aggregates support the following operations:
*   `Count`: Count of non-null field instances.
*   `Sum`: Cumulative sum of numeric values.
*   `Average`: Rolling mean.
*   `Min/Max`: Range extrema.
*   `Distinct Count`: Unique cardinalities.
*   `Custom`: User-provided Python script executing on the collected event list.

## Anomaly Detection (Z-Score)

Statistical outliers are flagged using a sliding rolling Z-Score model. For any aggregated window metric $X$, the Z-score is calculated relative to the rolling average $\mu$ and standard deviation $\sigma$ computed over the preceding $N$ windows:

$$Z = \frac{|X - \mu|}{\sigma}$$

If $Z > Z_{\text{threshold}}$ (where $Z_{\text{threshold}}$ is configured by the user, default 2.5), the value is flagged as an outlier. An anomaly alert is created in the database and triggers system-wide events.

## Workflow Integration Rules

System-generated alerts (Threshold breaches, statistical anomalies, connector failures, and recovery notifications) are linked to the **Workflow Automation Engine**.

When an alert fires:
1. The `StreamAlertService` queries all active workflows.
2. If a workflow contains a `stream_processor` native node configured for the stream ID and matches the trigger alert types, it triggers execution automatically.
3. The alert payload (stream ID, metric values, alert type, messages) is passed to the workflow run context as `initial_variables`, allowing downstream nodes (like notifications, cleaning, or reports compilation) to consume real-time alert data directly.
