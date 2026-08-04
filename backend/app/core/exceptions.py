"""
Custom Exceptions and Error Handling
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base exception for application"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "APP_ERROR"
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(AppException):
    """Authentication related errors"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED, error_code="AUTH_ERROR")


class AuthorizationError(AppException):
    """Authorization/permission errors"""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, error_code="FORBIDDEN")


class NotFoundError(AppException):
    """Resource not found"""

    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, error_code="NOT_FOUND")


class ValidationError(AppException):
    """Data validation errors"""

    def __init__(self, message: str, details: Dict[str, Any]):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class RateLimitError(AppException):
    """Rate limit exceeded"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message=message, status_code=status.HTTP_429_TOO_MANY_REQUESTS, error_code="RATE_LIMIT")


async def handle_exception(request: Request, exc: AppException) -> JSONResponse:
    """Global exception handler"""
    logger.error(
        f"Exception: {exc.error_code} - {exc.message}",
        extra={"path": request.url.path, "method": request.method, "details": exc.details},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path),
            }
        },
    )
