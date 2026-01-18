"""Custom exceptions for nsn-odds-data microservice."""

from typing import Any


class OddsAPIError(Exception):
    """Base exception for all odds API errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or "ODDS_API_ERROR"
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dict for API response."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class RateLimitError(OddsAPIError):
    """Rate limit exceeded on Odds-API.io."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: int | None = None,
        remaining_requests: int | None = None,
    ):
        details = {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        if remaining_requests is not None:
            details["remaining_requests"] = remaining_requests

        super().__init__(message, code="RATE_LIMIT_EXCEEDED", details=details)
        self.retry_after = retry_after
        self.remaining_requests = remaining_requests


class ProviderTimeoutError(OddsAPIError):
    """Timeout when calling Odds-API.io."""

    def __init__(
        self,
        message: str = "Provider request timed out",
        *,
        timeout_seconds: float | None = None,
        endpoint: str | None = None,
    ):
        details = {}
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        if endpoint is not None:
            details["endpoint"] = endpoint

        super().__init__(message, code="PROVIDER_TIMEOUT", details=details)


class EventNotFoundError(OddsAPIError):
    """Event not found on Odds-API.io."""

    def __init__(
        self,
        event_id: str,
        message: str | None = None,
    ):
        super().__init__(
            message or f"Event not found: {event_id}",
            code="EVENT_NOT_FOUND",
            details={"event_id": event_id},
        )
        self.event_id = event_id


class ProviderError(OddsAPIError):
    """Generic provider error (HTTP 4xx/5xx)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        endpoint: str | None = None,
    ):
        details = {}
        if status_code is not None:
            details["status_code"] = status_code
        if response_body is not None:
            details["response_body"] = response_body[:500]  # Truncate
        if endpoint is not None:
            details["endpoint"] = endpoint

        super().__init__(message, code="PROVIDER_ERROR", details=details)
        self.status_code = status_code


class ValidationError(OddsAPIError):
    """Invalid input data."""

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: Any = None,
    ):
        details = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)[:100]  # Truncate

        super().__init__(message, code="VALIDATION_ERROR", details=details)


class CacheError(OddsAPIError):
    """Redis cache operation failed."""

    def __init__(
        self,
        message: str = "Cache operation failed",
        *,
        operation: str | None = None,
        key: str | None = None,
    ):
        details = {}
        if operation is not None:
            details["operation"] = operation
        if key is not None:
            details["key"] = key

        super().__init__(message, code="CACHE_ERROR", details=details)


class DatabaseError(OddsAPIError):
    """Database operation failed."""

    def __init__(
        self,
        message: str = "Database operation failed",
        *,
        operation: str | None = None,
        table: str | None = None,
    ):
        details = {}
        if operation is not None:
            details["operation"] = operation
        if table is not None:
            details["table"] = table

        super().__init__(message, code="DATABASE_ERROR", details=details)
