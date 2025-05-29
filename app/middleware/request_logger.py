# app/middleware/request_logger.py
import json
import time
import traceback
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.common.db_logging.factory import DBLoggerFactory, global_logger_factory
from app.config.settings import settings
from app.models.models_request_response import AppRequestLog
from app.utils.direct_logger import ensure_sqlite_table_exists, log_request_direct
from app.utils.logger import generate_correlation_id, logger, set_correlation_id

# Ensure SQLite table exists
if not ensure_sqlite_table_exists():
    logger.warning("Failed to init SQLite table for API logs.")

class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for correlation ID generation and propagation
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.correlation_header = settings.CORRELATION_ID_HEADER
        self.enable_correlation = settings.ENABLE_CORRELATION_ID

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Generate or extract correlation ID and set it in context"""

        correlation_id = None

        if self.enable_correlation:
            # Try to get correlation ID from request headers
            correlation_id = self._get_correlation_id_from_request(request)

            # Generate new correlation ID if none provided
            if not correlation_id:
                correlation_id = generate_correlation_id()

            # Set correlation ID in context for this request
            set_correlation_id(correlation_id)

            # Store in request state for access in route handlers
            request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers if enabled
        if self.enable_correlation and correlation_id:
            response.headers[self.correlation_header] = correlation_id

        return response

    def _get_correlation_id_from_request(self, request: Request) -> Optional[str]:
        """Extract correlation ID from request headers"""

        # Check multiple possible header names
        possible_headers = [
            self.correlation_header,
            "X-Request-ID",
            "X-Trace-ID",
            "Request-ID",
            "Trace-ID"
        ]

        for header in possible_headers:
            value = request.headers.get(header)
            if value:
                return value

        return None


class EnhancedRequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Enhanced request logger with correlation tracking and database logging
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.log_to_db = True  # Will be configurable based on LOG_DB_URL

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Log request/response with correlation tracking"""

        start_time = time.time()

        # Get correlation ID from request state (set by CorrelationMiddleware)
        correlation_id = getattr(request.state, 'correlation_id', None)
        request_id = correlation_id or str(uuid.uuid4())

        # Set logging context for this request
        logger.set_context(
            correlation_id=correlation_id,
            request_id=request_id,
        )

        # Extract request information
        client_ip = self._get_client_ip(request)
        request_info = await self._extract_request_info(request)

        # Log incoming request
        logger.info(
            f"Incoming {request.method} {request.url.path}",
            extra={
                "event_type": "request_start",
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type"),
                "request_size": len(request_info.get("body_raw", b"")),
            }
        )

        # Process request and handle exceptions
        response = None
        error_info = None

        try:
            response = await call_next(request)
        except Exception as exc:
            error_info = {
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "traceback": traceback.format_exc()
            }

            logger.error(
                f"Request failed: {str(exc)}",
                extra={
                    "event_type": "request_error",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )

            # Create error response
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error", "correlation_id": correlation_id}
            )

            # Re-raise to maintain FastAPI error handling
            raise

        # Calculate execution time
        execution_time_ms = round((time.time() - start_time) * 1000, 2)

        # Extract response information
        response_info = await self._extract_response_info(response)

        # Add timing headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{execution_time_ms}ms"
        if correlation_id:
            response.headers[settings.CORRELATION_ID_HEADER] = correlation_id

        # Log completed request
        logger.info(
            f"Completed {request.method} {request.url.path} - {response.status_code}",
            extra={
                "event_type": "request_complete",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "execution_time_ms": execution_time_ms,
                "response_size": len(response_info.get("body_raw", b"")),
                "error": error_info,
            }
        )

        # Store in database if configured
        if self.log_to_db:
            await self._log_to_database(
                correlation_id=correlation_id,
                request_id=request_id,
                request=request,
                response=response,
                request_info=request_info,
                response_info=response_info,
                execution_time_ms=execution_time_ms,
                client_ip=client_ip,
                error_info=error_info
            )

        # Clear logging context
        logger.clear_context()

        return response

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request"""

        # Check for forwarded headers first
        forwarded_ips = [
            request.headers.get("X-Forwarded-For"),
            request.headers.get("X-Real-IP"),
            request.headers.get("CF-Connecting-IP"),  # Cloudflare
        ]

        for ip in forwarded_ips:
            if ip:
                # X-Forwarded-For can contain multiple IPs, take the first one
                return ip.split(",")[0].strip()

        # Fallback to direct client IP
        return request.client.host if request.client else None

    async def _extract_request_info(self, request: Request) -> dict:
        """Extract request information for logging"""

        try:
            # Read request body
            body_raw = await request.body()

            # Try to parse as JSON
            body_json = None
            if body_raw:
                try:
                    body_json = json.loads(body_raw.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            # Filter sensitive headers
            headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ['authorization', 'cookie', 'x-api-key']
            }

            return {
                "body_raw": body_raw,
                "body_json": body_json,
                "headers": headers,
                "query_params": dict(request.query_params),
            }

        except Exception as e:
            logger.warning(f"Failed to extract request info: {e}")
            return {}

    async def _extract_response_info(self, response: Response) -> dict:
        """Extract response information for logging"""

        try:
            body_raw = b""
            body_json = None

            if hasattr(response, 'body_iterator'):
                # Handle streaming responses
                chunks = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk)
                body_raw = b"".join(chunks)

                # Reset the iterator for actual response
                response.body_iterator = iterate_in_threadpool(iter(chunks))
            elif hasattr(response, 'body'):
                body_raw = response.body

            # Try to parse response as JSON
            if body_raw:
                try:
                    body_json = json.loads(body_raw.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            return {
                "body_raw": body_raw,
                "body_json": body_json,
                "headers": dict(response.headers),
            }

        except Exception as e:
            logger.warning(f"Failed to extract response info: {e}")
            return {}

    async def _log_to_database(self, **log_data):
        """Log request/response to database using the pluggable backend"""

        try:
            # Import here to avoid circular imports
            from app.core.logging_backend import log_api_request

            # Prepare log data for database storage
            db_log_data = {
                "correlation_id": log_data.get("correlation_id"),
                "request_id": log_data.get("request_id"),
                "timestamp": datetime.utcnow(),
                "method": log_data.get("request").method,
                "path": log_data.get("request").url.path,
                "url": str(log_data.get("request").url),
                "query_params": log_data.get("request_info", {}).get("query_params"),
                "headers": log_data.get("request_info", {}).get("headers"),
                "body": log_data.get("request_info", {}).get("body_json"),
                "body_size": len(log_data.get("request_info", {}).get("body_raw", b"")),
                "status_code": log_data.get("response").status_code,
                "response_headers": log_data.get("response_info", {}).get("headers"),
                "response_body": log_data.get("response_info", {}).get("body_json"),
                "response_size": len(log_data.get("response_info", {}).get("body_raw", b"")),
                "execution_time_ms": log_data.get("execution_time_ms"),
                "client_ip": log_data.get("client_ip"),
                "user_agent": log_data.get("request").headers.get("user-agent"),
                "account_id": log_data.get("account_id"),
                "partner_journey_id": log_data.get("partner_journey_id"),
                "application_id": getattr(log_data.get("request").state, "application_id", None),
                "user_id": getattr(log_data.get("request").state, "user_id", None),
                "error_message": log_data.get("error_info", {}).get("error_message") if log_data.get("error_info") else None,
                "error_type": log_data.get("error_info", {}).get("error_type") if log_data.get("error_info") else None,
            }

            # Log to database
            success = await log_api_request(**db_log_data)

            if success:
                logger.debug(
                    "Request logged to database successfully",
                    extra={
                        "event_type": "db_log_success",
                        "table": settings.API_LOG_TABLE,
                        "correlation_id": log_data.get("correlation_id"),
                    }
                )
            else:
                logger.warning(
                    "Failed to log request to database",
                    extra={
                        "event_type": "db_log_failure",
                        "table": settings.API_LOG_TABLE,
                        "correlation_id": log_data.get("correlation_id"),
                    }
                )

        except Exception as e:
            logger.error(
                f"Exception while logging to database: {e}",
                extra={
                    "event_type": "db_log_exception",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "correlation_id": log_data.get("correlation_id"),
                }
            )


# Combine both middlewares for a complete solution
def setup_logging_middlewares(app: FastAPI):
    """Setup all logging-related middlewares"""

    # Add correlation middleware first (runs last, returns first)
    app.add_middleware(CorrelationMiddleware)

    # Add request logging middleware
    app.add_middleware(EnhancedRequestLoggerMiddleware)
