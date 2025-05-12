import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.utils.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request, log timing info, and handle errors
        """
        # Check if request ID already exists in headers
        request_id = self._get_or_create_request_id(request)
        
        # Add request_id to request state for access in endpoint functions
        request.state.request_id = request_id
        
        # Store start time for performance measurement
        start_time = time.time()
        request.state.start_time = start_time
        
        # Extract relevant request data
        path = request.url.path
        method = request.method
        client_host = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent", "")
        content_length = request.headers.get("Content-Length", "0")
        
        # Set request context in logger
        logger.set_context(request_id=request_id)
        
        # Log request
        logger.info(
            f"Request started: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "client_host": client_host,
                "user_agent": user_agent,
                "content_length": content_length,
            },
        )
        
        # Process request and get response
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            process_time_ms = round(process_time * 1000, 2)
            
            # Log response
            logger.info(
                f"Request completed: {method} {path} - {response.status_code}",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "process_time_ms": process_time_ms,
                },
            )
            
            # Add request_id to response headers if not already set
            # (will be set by our response utility but adding as fallback)
            if "X-Request-ID" not in response.headers:
                response.headers["X-Request-ID"] = request_id
            
            # Add timing header if not already set
            if "X-Response-Time" not in response.headers:
                response.headers["X-Response-Time"] = f"{process_time_ms}ms"
            
            return response
            
        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time
            process_time_ms = round(process_time * 1000, 2)
            
            # Log error
            logger.error(
                f"Request failed: {method} {path}",
                exc_info=True,
                extra={
                    "method": method,
                    "path": path,
                    "process_time_ms": process_time_ms,
                    "error": str(e),
                },
            )
            
            # Re-raise the exception to be handled by the exception handlers
            raise
    
    def _get_or_create_request_id(self, request: Request) -> str:
        """
        Get request ID from headers or create a new one
        
        Args:
            request: The FastAPI request
            
        Returns:
            request_id: The request ID string
        """
        # Check standard request ID headers
        for header in ["X-Request-ID", "X-Correlation-ID", "Request-ID"]:
            if header in request.headers:
                return request.headers[header]
        
        # Generate a new request ID if none exists
        return str(uuid.uuid4())
