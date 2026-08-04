import gzip
import io
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, StreamingResponse

from app.services.performance_service import performance_service

logger = logging.getLogger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """Custom ASGI Middleware to dynamically compress API payloads and record telemetry metrics."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # 1. Inspect Accept-Encoding header
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "gzip" not in accept_encoding:
            return response

        # 2. Skip compression for already encoded resources or heavy streaming/binary files
        content_encoding = response.headers.get("Content-Encoding")
        content_type = response.headers.get("Content-Type", "")

        if content_encoding or content_type in [
            "application/zip",
            "application/x-gzip",
            "image/png",
            "image/jpeg",
            "image/gif",
            "application/octet-stream",
            "application/pdf",
        ]:
            return response

        # 3. Read body from non-streaming responses and compress
        if not isinstance(response, StreamingResponse):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            original_size = len(body)
            # Only compress responses larger than 1000 bytes
            if original_size < 1000:
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

            # Compress using gzip
            gzip_buffer = io.BytesIO()
            with gzip.GzipFile(mode="wb", fileobj=gzip_buffer) as f:
                f.write(body)
            compressed_body = gzip_buffer.getvalue()
            compressed_size = len(compressed_body)

            # Record telemetry sizes
            performance_service.record_compression(original_size, compressed_size)

            # Construct new headers
            headers = dict(response.headers)
            headers["Content-Encoding"] = "gzip"
            headers["Content-Length"] = str(compressed_size)
            headers.pop("content-length", None)  # Remove standard duplicate key casing

            return Response(
                content=compressed_body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )

        return response
