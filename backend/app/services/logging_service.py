import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variables for request tracing
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for python logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Inject trace context
        log_data["request_id"] = request_id_var.get("-")
        log_data["user_id"] = user_id_var.get("-")

        # Merge extra parameters passed via logging (e.g. logger.info("msg", extra={...}))
        if hasattr(record, "extra_info"):
            log_data.update(record.extra_info)
        elif isinstance(record.args, dict) and record.args:
            # Safely check if args can be treated as dict
            log_data.update(record.args)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO"):
    """
    Configures application loggers to output JSON logs.
    """
    root_logger = logging.getLogger()
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Generate/Retrieve Request ID
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_token = request_id_var.set(req_id)

        # 2. Try parsing JWT for user_id (if authorization header present)
        user_id = "-"
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                from app.core.security import decode_token

                payload = decode_token(token)
                if payload and "sub" in payload:
                    user_id = payload["sub"]
            except Exception:
                pass

        user_id_token = user_id_var.set(user_id)

        # 3. Request details
        method = request.method
        endpoint = request.url.path
        ip_address = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "-")

        # Increment active requests gauge
        from app.services.monitoring_service import monitoring_service

        monitoring_service.increment_active_requests()

        start_time = time.time()
        try:
            response: Response = await call_next(request)

            # Post-dispatch user_id check
            if hasattr(request.state, "user_id"):
                user_id = request.state.user_id
                user_id_var.set(user_id)

            execution_time_ms = int((time.time() - start_time) * 1000)
            status_code = response.status_code

            response_size = 0
            if "content-length" in response.headers:
                try:
                    response_size = int(response.headers["content-length"])
                except ValueError:
                    pass

            # Record metrics
            monitoring_service.record_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration_sec=execution_time_ms / 1000.0,
                response_size_bytes=response_size,
            )

            # Structured HTTP Request Log
            log_extra = {
                "extra_info": {
                    "request_id": req_id,
                    "user_id": user_id,
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": status_code,
                    "execution_time_ms": execution_time_ms,
                    "ip_address": ip_address,
                    "response_size_bytes": response_size,
                }
            }
            logger = logging.getLogger("app.request")
            logger.info(f"HTTP Request {method} {endpoint} - {status_code}", extra=log_extra)

            response.headers["X-Request-ID"] = req_id
            return response

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            status_code = 500

            monitoring_service.record_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration_sec=execution_time_ms / 1000.0,
                response_size_bytes=0,
            )

            log_extra = {
                "extra_info": {
                    "request_id": req_id,
                    "user_id": user_id,
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": status_code,
                    "execution_time_ms": execution_time_ms,
                    "ip_address": ip_address,
                    "error": str(e),
                }
            }
            logger = logging.getLogger("app.request")
            logger.error(f"HTTP Request {method} {endpoint} Failed - {str(e)}", extra=log_extra)
            raise e

        finally:
            monitoring_service.decrement_active_requests()
            request_id_var.reset(request_id_token)
            user_id_var.reset(user_id_token)
