# Real-Time Ingestion and Streaming Engine

This document provides details on the architectural design, event lifecycle, ingestion adapters, and buffering strategies implemented in the Real-Time Streaming Ingestion Engine.

## Ingestion Architecture

The streaming engine handles high-throughput continuous event streams fully offline. It operates asynchronously utilizing Python's `asyncio` event loop.

```
                  +----------------------------------------------+
                  |               Ingestion Source               |
                  +----------------------------------------------+
                    /          |             |        \        \
                   /           |             |         \        \
                  v            v             v          v        v
               +-----+      +------+      +----+      +----+  +----+
               | CSV |      | JSON |      | REST |    | WS |  | FS |
               +-----+      +------+      +----+      +----+  +----+
                  \            /             |          /        /
                   \          /              |         /        /
                    v        v               v        v        v
                  +----------------------------------------------+
                  |         Stream Ingestion Interface           |
                  +----------------------------------------------+
                                         |
                                         v
                  +----------------------------------------------+
                  |      Async Event Buffer (Queue maxsize)      |
                  +----------------------------------------------+
                                         |
                                         v
                  +----------------------------------------------+
                  |            Backpressure Router               |
                  +----------------------------------------------+
                    /                    |                    \
                   v                     v                     v
            (Block Producer)    (Drop Oldest Event)   (Drop Newest Event)
                                         |
                                         v
                  +----------------------------------------------+
                  |            Tumbling/Sliding Windows          |
                  +----------------------------------------------+
```

## Buffer Strategy & Backpressure

To prevent memory leaks and coordinate speed disparities between producers and consumer handlers, the streaming engine implements a bounded queue buffer using `asyncio.Queue` with three configurable backpressure resolution strategies:

1. **Block**: (Default) The producer's thread or task blocks and awaits queue capacity availability. This slows down REST push clients or halts tail reading.
2. **Drop Oldest**: Discards the event at the head of the buffer queue (oldest unhandled data) to accommodate the incoming event instantly.
3. **Drop Newest**: Rejects the incoming event, logging it immediately to the `streaming_dropped_events_total` telemetry gauge.

## Ingestion Adapters

The engine defines a pluggable `StreamAdapter` interface:

*   **CSV File Tailer**: Scans log files continuously, seeking additions, parsing rows as dictionaries.
*   **JSON Event Tailer**: Tails logs containing JSON lines and parses objects dynamically.
*   **Local REST Endpoint**: Exposes `/api/v1/streams/{id}/ingest` for HTTP clients to push events directly.
*   **WebSocket Ingress**: Opens a websocket endpoint under `/api/v1/streams/{id}/ws` for streaming JSON events.
*   **File System Monitor**: Scans watch folders for file deposits, parses `.json`/`.csv` arrivals, and renames processed files with a `.processed` suffix to guarantee exactly-once processing.
