import asyncio
import csv
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Awaitable

from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.stream import StreamConfig
from app.services.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)

# Extensible Adapter Interface
class StreamAdapter(ABC):
    @abstractmethod
    async def start(self, on_event: Callable[[Dict[str, Any]], Awaitable[None]], on_error: Callable[[Exception], Awaitable[None]]):
        pass

    @abstractmethod
    async def stop(self):
        pass


# 1. CSV File Tail Adapter
class CSVFileTailAdapter(StreamAdapter):
    def __init__(self, file_path: str, poll_interval_sec: float = 1.0):
        self.file_path = file_path
        self.poll_interval_sec = poll_interval_sec
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self, on_event: Callable[[Dict[str, Any]], Awaitable[None]], on_error: Callable[[Exception], Awaitable[None]]):
        self.running = True
        self.task = asyncio.create_task(self._tail_file(on_event, on_error))

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _tail_file(self, on_event: Callable[[Dict[str, Any]], Awaitable[None]], on_error: Callable[[Exception], Awaitable[None]]):
        try:
            if not os.path.exists(self.file_path):
                # Create parent directory and empty file if doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
                with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                    pass
            
            file_size = os.path.getsize(self.file_path)
            
            while self.running:
                await asyncio.sleep(self.poll_interval_sec)
                if not os.path.exists(self.file_path):
                    continue
                
                curr_size = os.path.getsize(self.file_path)
                if curr_size < file_size:
                    # File was truncated or recreated, reset
                    file_size = 0
                
                if curr_size > file_size:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        f.seek(file_size)
                        content = f.read()
                        file_size = curr_size
                        
                        # Parse lines using CSV reader
                        reader = csv.reader(content.splitlines())
                        for row in reader:
                            if row:
                                # Standard CSV tailing wraps rows as keys
                                event = {f"col_{i}": val for i, val in enumerate(row)}
                                await on_event(event)
        except Exception as e:
            logger.exception(f"Error tailing CSV file {self.file_path}")
            await on_error(e)


# 2. JSON Event Stream Adapter (Tails JSON lines)
class JSONEventStreamAdapter(StreamAdapter):
    def __init__(self, file_path: str, poll_interval_sec: float = 1.0):
        self.file_path = file_path
        self.poll_interval_sec = poll_interval_sec
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self, on_event: Callable[[Dict[str, Any]], Awaitable[None]], on_error: Callable[[Exception], Awaitable[None]]):
        self.running = True
        self.task = asyncio.create_task(self._tail_file(on_event, on_error))

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _tail_file(self, on_event: Callable[[Dict[str, Any]], Awaitable[None]], on_error: Callable[[Exception], Awaitable[None]]):
        try:
            if not os.path.exists(self.file_path):
                os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
                with open(self.file_path, "w", encoding="utf-8") as f:
                    pass
            
            file_size = os.path.getsize(self.file_path)
            
            while self.running:
                await asyncio.sleep(self.poll_interval_sec)
                if not os.path.exists(self.file_path):
                    continue
                
                curr_size = os.path.getsize(self.file_path)
                if curr_size < file_size:
                    file_size = 0
                
                if curr_size > file_size:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        f.seek(file_size)
                        content = f.read()
                        file_size = curr_size
                        
                        for line in content.splitlines():
                            line = line.strip()
                            if line:
                                try:
                                    event = json.loads(line)
                                    if isinstance(event, dict):
                                        await on_event(event)
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse JSON line: {line}")
        except Exception as e:
            logger.exception(f"Error tailing JSON file {self.file_path}")
            await on_error(e)


# 3. Local REST Event Ingestion Adapter
class LocalRESTAdapter(StreamAdapter):
    def __init__(self):
        self.on_event_cb: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None

    async def start(self, on_event: Callable[[Dict[str, Any]], Awaitable[None]], on_error: Callable[[Exception], Awaitable[None]]):
        self.on_event_cb = on_event

    async def stop(self):
        self.on_event_cb = None

    async def ingest_event(self, event: Dict[str, Any]):
        if self.on_event_cb:
            await self.on_event_cb(event)
        else:
            raise RuntimeError("REST adapter is not running or callback is not registered.")


# 4. Local WebSocket Ingestion Adapter
class LocalWebSocketAdapter(StreamAdapter):
    def __init__(self):
        self.on_event_cb: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
        self.active_websockets: Set[Any] = set()

    async def start(self, on_event: Callable[[Dict[str, Any]], Awaitable[None]], on_error: Callable[[Exception], Awaitable[None]]):
        self.on_event_cb = on_event

    async def stop(self):
        self.on_event_cb = None
        self.active_websockets.clear()

    async def handle_websocket(self, websocket: Any):
        self.active_websockets.add(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                if self.on_event_cb:
                    try:
                        event = json.loads(data)
                        if isinstance(event, dict):
                            await self.on_event_cb(event)
                    except json.JSONDecodeError:
                        logger.warning(f"WebSocket received invalid JSON payload: {data}")
        except Exception as e:
            logger.debug(f"WebSocket disconnected or errored: {e}")
        finally:
            self.active_websockets.discard(websocket)


# 5. File System Monitoring Adapter
class FileSystemMonitorAdapter(StreamAdapter):
    def __init__(self, dir_path: str, poll_interval_sec: float = 2.0):
        self.dir_path = dir_path
        self.poll_interval_sec = poll_interval_sec
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self, on_event: Callable[[Dict[str, Any]], Awaitable[None]], on_error: Callable[[Exception], Awaitable[None]]):
        self.running = True
        self.task = asyncio.create_task(self._monitor_dir(on_event, on_error))

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _monitor_dir(self, on_event: Callable[[Dict[str, Any]], Awaitable[None]], on_error: Callable[[Exception], Awaitable[None]]):
        try:
            if not os.path.exists(self.dir_path):
                os.makedirs(self.dir_path, exist_ok=True)
            
            while self.running:
                await asyncio.sleep(self.poll_interval_sec)
                
                # Scan directory for non-processed files
                for item in os.listdir(self.dir_path):
                    item_path = os.path.join(self.dir_path, item)
                    if os.path.isfile(item_path) and not item.endswith(".processed") and not item.startswith("."):
                        try:
                            # Read file
                            if item.endswith(".json"):
                                with open(item_path, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    if isinstance(data, list):
                                        for event in data:
                                            if isinstance(event, dict):
                                                await on_event(event)
                                    elif isinstance(data, dict):
                                        await on_event(data)
                            elif item.endswith(".csv"):
                                with open(item_path, "r", encoding="utf-8") as f:
                                    reader = csv.DictReader(f)
                                    for row in reader:
                                        await on_event(dict(row))
                            
                            # Mark as processed by renaming
                            os.rename(item_path, item_path + ".processed")
                        except Exception as file_err:
                            logger.error(f"Error processing folder file {item_path}: {file_err}")
        except Exception as e:
            logger.exception(f"Error monitoring directory {self.dir_path}")
            await on_error(e)


# Window State representation
class ProcessingWindow:
    def __init__(self, start_time: datetime, end_time: datetime):
        self.start_time = start_time
        self.end_time = end_time
        self.events: List[Dict[str, Any]] = []


# Main Streaming Service
class StreamingService:
    def __init__(self):
        # Maps stream_id -> Active asyncio Task running queue-consumer loop
        self.active_consumers: Dict[str, asyncio.Task] = {}
        # Maps stream_id -> Adapter instances
        self.adapters: Dict[str, StreamAdapter] = {}
        # Maps stream_id -> queue
        self.queues: Dict[str, asyncio.Queue] = {}
        # Maps stream_id -> list of open ProcessingWindows
        self.windows: Dict[str, List[ProcessingWindow]] = {}
        # In-memory sliding buffer for last N raw events across streams
        self.recent_events_buffer = deque(maxlen=200)
        # Session window gap tracking: stream_id -> last event timestamp
        self.session_last_seen: Dict[str, datetime] = {}
        # session active window: stream_id -> ProcessingWindow
        self.active_session_window: Dict[str, ProcessingWindow] = {}

    def get_adapter(self, stream_id: str) -> Optional[StreamAdapter]:
        return self.adapters.get(stream_id)

    async def register_incremental_knowledge_graph(self, stream: StreamConfig, user_id: str):
        """Lineage tracking interface."""
        try:
            from app.services.knowledge_graph_service import knowledge_graph_service
            await knowledge_graph_service.register_stream_incrementally(stream, user_id)
        except Exception as e:
            logger.error(f"Knowledge graph registration failed: {e}")

    async def start_stream(self, stream_id: str, user_id: str):
        """Starts ingestion thread-workers and queue loops."""
        async with AsyncSessionLocal() as session:
            stream = (await session.execute(
                select(StreamConfig).where(StreamConfig.id == stream_id)
            )).scalar_one_or_none()

            if not stream:
                raise ValueError(f"Stream configuration '{stream_id}' not found.")

            if stream_id in self.active_consumers:
                logger.info(f"Stream {stream_id} is already running.")
                return

            source_config = json.loads(stream.source_config)
            max_queue_size = int(source_config.get("max_queue_size", 1000))
            backpressure_strategy = source_config.get("backpressure_strategy", "block")  # block, drop_oldest, drop_newest

            # Create queue
            queue = asyncio.Queue(maxsize=max_queue_size)
            self.queues[stream_id] = queue
            self.windows[stream_id] = []

            # Instantiate corresponding adapter
            adapter: StreamAdapter
            if stream.source_type == "csv":
                adapter = CSVFileTailAdapter(source_config["file_path"], float(source_config.get("poll_interval_sec", 1.0)))
            elif stream.source_type == "json":
                adapter = JSONEventStreamAdapter(source_config["file_path"], float(source_config.get("poll_interval_sec", 1.0)))
            elif stream.source_type == "rest":
                adapter = LocalRESTAdapter()
            elif stream.source_type == "websocket":
                adapter = LocalWebSocketAdapter()
            elif stream.source_type == "fs":
                adapter = FileSystemMonitorAdapter(source_config["dir_path"], float(source_config.get("poll_interval_sec", 2.0)))
            else:
                raise NotImplementedError(f"Stream source type '{stream.source_type}' not supported.")

            self.adapters[stream_id] = adapter

            # Define ingestion callback
            async def on_event(event_data: Dict[str, Any]):
                # Add timestamp if missing
                if "_timestamp" not in event_data:
                    event_data["_timestamp"] = datetime.utcnow().isoformat()
                event_data["_stream_id"] = stream_id
                event_data["_stream_name"] = stream.name

                # Append to sliding recent raw event buffer
                self.recent_events_buffer.append(event_data)
                monitoring_service.record_streaming_event(stream_id)

                # Queue push with Backpressure evaluation
                if queue.full():
                    if backpressure_strategy == "drop_oldest":
                        try:
                            # Drop head
                            queue.get_nowait()
                            monitoring_service.record_dropped_event(stream_id)
                            await queue.put(event_data)
                        except asyncio.QueueEmpty:
                            await queue.put(event_data)
                    elif backpressure_strategy == "drop_newest":
                        monitoring_service.record_dropped_event(stream_id)
                        # Drop incoming event
                        return
                    else:
                        # block strategy: wait until space is available
                        await queue.put(event_data)
                else:
                    await queue.put(event_data)

                # Set queue depth metric
                monitoring_service.set_stream_queue_depth(stream_id, queue.qsize())

            async def on_error(exc: Exception):
                logger.error(f"Ingestion adapter exception on stream {stream_id}: {exc}")
                from app.services.stream_alert_service import stream_alert_service
                await stream_alert_service.trigger_failure_alert(stream_id, str(exc), user_id)

            # Start adapter ingestion
            await adapter.start(on_event, on_error)

            # Start queue consumer loop
            self.active_consumers[stream_id] = asyncio.create_task(
                self._consumer_processing_loop(stream_id, stream, user_id)
            )

            # Update DB state
            await session.execute(
                update(StreamConfig).where(StreamConfig.id == stream_id).values(active=True)
            )
            await session.commit()

            # KG incremental sync
            await self.register_incremental_knowledge_graph(stream, user_id)
            
            # Update metrics
            monitoring_service.set_active_streams(len(self.active_consumers))
            logger.info(f"Stream {stream_id} started successfully.")

    async def stop_stream(self, stream_id: str, user_id: str):
        """Stops ingestion workers and queue consumer tasks."""
        if stream_id not in self.active_consumers:
            logger.info(f"Stream {stream_id} is not active.")
            return

        # Cancel queue processing consumer loop
        task = self.active_consumers.pop(stream_id)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Stop Ingestion Adapter
        adapter = self.adapters.pop(stream_id, None)
        if adapter:
            await adapter.stop()

        # Clean configurations
        self.queues.pop(stream_id, None)
        self.windows.pop(stream_id, None)
        self.session_last_seen.pop(stream_id, None)
        self.active_session_window.pop(stream_id, None)

        async with AsyncSessionLocal() as session:
            await session.execute(
                update(StreamConfig).where(StreamConfig.id == stream_id).values(active=False)
            )
            await session.commit()

        monitoring_service.set_active_streams(len(self.active_consumers))
        logger.info(f"Stream {stream_id} stopped.")

    async def _consumer_processing_loop(self, stream_id: str, stream: StreamConfig, user_id: str):
        queue = self.queues[stream_id]
        
        # Load window settings
        window_type = stream.window_type
        window_size_sec = 10
        slide_size_sec = 5
        session_gap_sec = 5

        if stream.window_size_sec:
            try:
                win_conf = json.loads(stream.window_size_sec)
                if isinstance(win_conf, dict):
                    window_size_sec = int(win_conf.get("size_sec", 10))
                    slide_size_sec = int(win_conf.get("slide_sec", 5))
                    session_gap_sec = int(win_conf.get("gap_sec", 5))
                else:
                    window_size_sec = int(win_conf)
            except Exception:
                try:
                    window_size_sec = int(stream.window_size_sec)
                except ValueError:
                    pass

        # Maintain window scheduling trigger timers
        last_tumble_trigger = datetime.utcnow()
        last_slide_trigger = datetime.utcnow()

        while True:
            try:
                # Poll queue
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    monitoring_service.set_stream_queue_depth(stream_id, queue.qsize())
                except asyncio.TimeoutError:
                    # Timeout polling: evaluate window timeouts on idle
                    event = None

                now = datetime.utcnow()

                # Process Event if available
                if event:
                    event_ts = datetime.fromisoformat(event["_timestamp"])
                    
                    # 1. Assign to Tumbling Windows
                    if window_type == "tumbling":
                        # If no window is open, open a tumbling window starting now
                        if not self.windows[stream_id]:
                            w_start = now
                            w_end = w_start + timedelta(seconds=window_size_sec)
                            self.windows[stream_id].append(ProcessingWindow(w_start, w_end))
                        
                        # Add to active window
                        self.windows[stream_id][0].events.append(event)

                    # 2. Assign to Sliding Windows
                    elif window_type == "sliding":
                        # Open new sliding windows dynamically if slide duration elapsed
                        if not self.windows[stream_id] or (now - last_slide_trigger).total_seconds() >= slide_size_sec:
                            w_start = now
                            w_end = w_start + timedelta(seconds=window_size_sec)
                            self.windows[stream_id].append(ProcessingWindow(w_start, w_end))
                            last_slide_trigger = now
                        
                        # Add event to ALL overlapping windows
                        for window in self.windows[stream_id]:
                            if window.start_time <= now <= window.end_time:
                                window.events.append(event)

                    # 3. Assign to Session Windows
                    elif window_type == "session":
                        last_seen = self.session_last_seen.get(stream_id)
                        if not last_seen or (now - last_seen).total_seconds() >= session_gap_sec:
                            # Trigger previous window evaluation if gap exceeded before creating a new one
                            if stream_id in self.active_session_window:
                                await self._evaluate_and_trigger_window(
                                    stream_id, self.active_session_window[stream_id], stream, user_id
                                )
                            # Create new session window
                            self.active_session_window[stream_id] = ProcessingWindow(now, now + timedelta(seconds=session_gap_sec))
                        
                        # Update session activity
                        self.session_last_seen[stream_id] = now
                        self.active_session_window[stream_id].events.append(event)
                        # Session window end time pushes out
                        self.active_session_window[stream_id].end_time = now + timedelta(seconds=session_gap_sec)

                    queue.task_done()

                # Evaluate window closures based on system time
                now = datetime.utcnow()
                if window_type == "tumbling" and self.windows[stream_id]:
                    # Tumbling window closes when end time passes
                    win = self.windows[stream_id][0]
                    if now >= win.end_time:
                        self.windows[stream_id].pop(0)
                        await self._evaluate_and_trigger_window(stream_id, win, stream, user_id)
                        
                        # Open next tumbling window immediately
                        w_start = now
                        w_end = w_start + timedelta(seconds=window_size_sec)
                        self.windows[stream_id].append(ProcessingWindow(w_start, w_end))

                elif window_type == "sliding" and self.windows[stream_id]:
                    # Close sliding windows that expired
                    expired_windows = [w for w in self.windows[stream_id] if now >= w.end_time]
                    for win in expired_windows:
                        self.windows[stream_id].remove(win)
                        await self._evaluate_and_trigger_window(stream_id, win, stream, user_id)

                elif window_type == "session" and stream_id in self.active_session_window:
                    # Session window closes when gap is exceeded with inactivity
                    last_seen = self.session_last_seen.get(stream_id)
                    if last_seen and (now - last_seen).total_seconds() >= session_gap_sec:
                        win = self.active_session_window.pop(stream_id)
                        await self._evaluate_and_trigger_window(stream_id, win, stream, user_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Exception in stream consumer loop {stream_id}")
                await asyncio.sleep(1.0)

    async def _evaluate_and_trigger_window(self, stream_id: str, window: ProcessingWindow, stream: StreamConfig, user_id: str):
        """Processes window aggregates and sends report outputs to Analytics service."""
        start_time = time.time()
        events = window.events
        if not events:
            # Skip empty windows or output empty metrics
            return

        # Decode aggregations configuration
        # [{ "field": "sales", "op": "sum" }, { "field": "userId", "op": "distinct_count" }]
        aggs = []
        if stream.aggregations:
            try:
                aggs = json.loads(stream.aggregations)
            except Exception:
                pass

        results: Dict[str, Any] = {
            "_window_start": window.start_time.isoformat(),
            "_window_end": window.end_time.isoformat(),
            "_event_count": len(events)
        }

        # Perform aggregates
        for agg in aggs:
            field = agg.get("field")
            op = agg.get("op", "count").lower()
            label = agg.get("label", f"{op}_{field}")

            # Collect field values, filter nulls
            vals = []
            for ev in events:
                val = ev.get(field)
                if val is not None:
                    try:
                        vals.append(float(val))
                    except ValueError:
                        vals.append(val)

            # Evaluate operations
            if op == "count":
                results[label] = len(vals)
            elif op == "sum":
                results[label] = sum(v for v in vals if isinstance(v, (int, float)))
            elif op == "average":
                num_vals = [v for v in vals if isinstance(v, (int, float))]
                results[label] = sum(num_vals) / len(num_vals) if num_vals else 0.0
            elif op == "min":
                num_vals = [v for v in vals if isinstance(v, (int, float))]
                results[label] = min(num_vals) if num_vals else 0.0
            elif op == "max":
                num_vals = [v for v in vals if isinstance(v, (int, float))]
                results[label] = max(num_vals) if num_vals else 0.0
            elif op == "distinct_count":
                results[label] = len(set(vals))
            elif op == "custom" and agg.get("code"):
                # Run custom aggregation
                try:
                    # Provide 'events' context
                    local_scope = {"events": events, "result": None}
                    exec(agg["code"], {}, local_scope)
                    results[label] = local_scope["result"]
                except Exception as eval_err:
                    logger.error(f"Error evaluating custom aggregation: {eval_err}")
                    results[label] = None

        # Track execution time
        duration = time.time() - start_time
        monitoring_service.record_window_execution(stream_id, stream.window_type, duration)

        logger.info(f"Stream {stream_id} window triggered: {len(events)} events aggregated in {duration:.4f}s.")

        # Forward output results to Streaming Analytics Engine
        try:
            from app.services.stream_analytics_service import stream_analytics_service
            await stream_analytics_service.process_window_results(stream_id, results, user_id)
        except Exception as e:
            logger.exception(f"Analytics service processing error: {e}")


streaming_service = StreamingService()
