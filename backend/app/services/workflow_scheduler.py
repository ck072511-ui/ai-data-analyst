import asyncio
import logging
import threading
import sys
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.workflow import WorkflowSchedule, WorkflowExecution
from app.services.workflow_engine import workflow_engine

logger = logging.getLogger(__name__)

def parse_cron_field(field: str, val_range: range) -> set:
    """Parses a single cron field and returns the matching values as a set."""
    if field == "*":
        return set(val_range)
    
    values = set()
    for part in field.split(","):
        if "/" in part:
            base, step = part.split("/")
            step_val = int(step)
            if base == "*":
                # */5 -> match multiples of 5 within range
                for v in val_range:
                    if v % step_val == 0:
                        values.add(v)
            else:
                start_val = int(base)
                for v in range(start_val, val_range.stop, step_val):
                    if v in val_range:
                        values.add(v)
        elif "-" in part:
            start, end = part.split("-")
            for v in range(int(start), int(end) + 1):
                if v in val_range:
                    values.add(v)
        else:
            values.add(int(part))
    return values

def get_next_cron_run(cron_expr: str, start_dt: datetime) -> datetime:
    """Calculates the next run datetime based on a 5-field cron expression."""
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}. Must contain 5 fields.")

    min_field, hour_field, dom_field, month_field, dow_field = fields

    # Define valid ranges (1-indexed for months/days/weekdays)
    min_set = parse_cron_field(min_field, range(0, 60))
    hour_set = parse_cron_field(hour_field, range(0, 24))
    dom_set = parse_cron_field(dom_field, range(1, 32))
    month_set = parse_cron_field(month_field, range(1, 13))
    # Python weekday: 0=Monday, 6=Sunday. Cron weekday: 0-6 (Sunday-Saturday, or 0/7=Sunday)
    # We map Sunday (0 or 7) -> 6, Monday (1) -> 0, etc.
    raw_dow_set = parse_cron_field(dow_field, range(0, 8)) # 0 to 7
    dow_set = set()
    for d in raw_dow_set:
        if d in [0, 7]:
            dow_set.add(6) # Sunday
        else:
            dow_set.add(d - 1) # Map 1-6 -> 0-5 (Mon-Sat)

    # Search minute-by-minute starting 1 minute from start_dt
    curr = start_dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
    # Stop searching after 1 year to prevent infinite loop
    max_search = start_dt + timedelta(days=366)

    while curr < max_search:
        if curr.minute in min_set:
            if curr.hour in hour_set:
                if curr.day in dom_set:
                    if curr.month in month_set:
                        if curr.weekday() in dow_set:
                            return curr
        curr += timedelta(minutes=1)

    raise ValueError(f"Could not calculate next run time for cron: {cron_expr}")

def calculate_next_run(schedule_type: str, cron_expression: Optional[str], start_dt: datetime) -> Optional[datetime]:
    """Calculates the next scheduled execution datetime based on the schedule type."""
    if schedule_type == "one_time":
        return None
    elif schedule_type == "daily":
        return start_dt + timedelta(days=1)
    elif schedule_type == "weekly":
        return start_dt + timedelta(weeks=1)
    elif schedule_type == "monthly":
        # Add 30 days approximately, or compute exact next month date
        next_month = start_dt.month + 1 if start_dt.month < 12 else 1
        next_year = start_dt.year if start_dt.month < 12 else start_dt.year + 1
        try:
            return start_dt.replace(year=next_year, month=next_month)
        except ValueError:
            # Handle month end day index errors
            return start_dt.replace(year=next_year, month=next_month, day=28)
    elif schedule_type == "cron":
        if not cron_expression:
            raise ValueError("cron_expression is missing.")
        return get_next_cron_run(cron_expression, start_dt)
    return None

class WorkflowScheduler:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Starts the background scheduler loop in a daemon thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop)
        self._thread.daemon = True
        self._thread.start()
        logger.info("Workflow scheduler daemon started.")

    def stop(self):
        """Stops the scheduler loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            logger.info("Workflow scheduler daemon stopped.")

    def _scheduler_loop(self):
        # Create event loop for the async scheduler actions in this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self._running:
            try:
                loop.run_until_complete(self._check_and_trigger_schedules())
            except Exception as e:
                logger.error(f"Error in scheduler tick: {e}")
            
            # Tick every 10 seconds
            for _ in range(10):
                if not self._running:
                    break
                time_sleep = 1.0
                # Wait using standard sleep
                import time
                time.sleep(time_sleep)

    async def _check_and_trigger_schedules(self):
        now = datetime.utcnow()
        async with AsyncSessionLocal() as session:
            # Find active schedules due for run
            schedules = (await session.execute(
                select(WorkflowSchedule)
                .where(WorkflowSchedule.active == True)
                .where(WorkflowSchedule.next_run_at <= now)
            )).scalars().all()

            for sched in schedules:
                logger.info(f"Triggering scheduled run for workflow {sched.workflow_id} (Type: {sched.schedule_type})")
                
                # 1. Create a workflow execution history entry
                execution = WorkflowExecution(
                    workflow_id=sched.workflow_id,
                    status="pending",
                    started_at=datetime.utcnow(),
                    user_id=sched.user_id
                )
                session.add(execution)
                await session.commit()
                await session.refresh(execution)

                # 2. Trigger asynchronous execution of the workflow
                # We spin it up in the background as a Task
                asyncio.create_task(workflow_engine.execute_workflow(execution.id, sched.user_id))

                # 3. Calculate next run and update schedule
                try:
                    next_run = calculate_next_run(sched.schedule_type, sched.cron_expression, now)
                    if next_run:
                        sched.next_run_at = next_run
                    else:
                        # One time schedule completes
                        sched.active = False
                        sched.next_run_at = None
                except Exception as e:
                    logger.error(f"Failed to calculate next run for schedule {sched.id}: {e}")
                    sched.active = False # Deactivate on invalid formulas

                sched.updated_at = datetime.utcnow()
                session.add(sched)
                await session.commit()

workflow_scheduler = WorkflowScheduler()
