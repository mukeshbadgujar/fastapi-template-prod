# app/middleware/request_logger.py
import json
import time
import uuid
import traceback
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.concurrency import iterate_in_threadpool
from starlette.types import ASGIApp

from app.models.models_request_response import AppRequestLog
from app.common.db_logging.factory import DBLoggerFactory, global_logger_factory
from app.config.settings import settings
from app.utils.direct_logger import log_request_direct, ensure_sqlite_table_exists
from app.utils.logger import logger

# Ensure SQLite table exists
if not ensure_sqlite_table_exists():
    logger.warning("Failed to init SQLite table for API logs.")

class RequestLoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger_factory = global_logger_factory
        self.real_time = settings.API_LOG_REAL_TIME

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Removed redundant request_id creation
        request_id = self._get_or_create_request_id(request)
        request.state.request_id = request_id

        start = time.time()
        client_ip = request.client.host if request.client else None
        request_headers = {k: v for k, v in request.headers.items() if k.lower() not in ("authorization", "cookie")}

        # Read request body
        try:
            raw_body = await request.body()
            request_body = json.loads(raw_body) if raw_body else None
        except Exception:
            request_body = {"raw": raw_body.decode(errors="ignore")} if raw_body else None

        # Call downstream
        try:
            response = await call_next(request)
        except Exception as exc:
            response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
            error = str(exc)
            tb = traceback.format_exc()
            # Log error case, without response_body
            self._log(request_id, request, response, start, request_body, client_ip, request_headers, error)
            raise

        # Capture and re-attach response body for logging
        resp_body = None
        if hasattr(response, 'body_iterator'):
            # consume streaming response
            chunks = [chunk async for chunk in response.body_iterator]
            # reset iterator
            response.body_iterator = iterate_in_threadpool(iter(chunks))
            raw = b"".join(chunks)
            try:
                resp_body = json.loads(raw.decode('utf-8'))
            except Exception:
                resp_body = {"raw": raw.decode('utf-8', errors='ignore')} if raw else None
        else:
            # non-streaming response
            try:
                body_bytes = response.body
                text = body_bytes.decode(errors='ignore') if body_bytes else None
                resp_body = json.loads(text) if text else None
            except Exception:
                resp_body = None

        # Attach headers
        exec_ms = round((time.time() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{exec_ms}ms"

        # Log
        self._log(
            request_id=request_id,
            request=request,
            response=response,
            start=start,
            request_body=request_body,
            client_ip=client_ip,
            request_headers=request_headers,
            response_body=resp_body,
            error=None,
        )
        return response

    def _log(
        self,
        request_id: str,
        request: Request,
        response: Response,
        start: float,
        request_body,
        client_ip: str,
        request_headers: dict,
        response_body=None,
        error: str = None,
    ):
        duration = round((time.time() - start) * 1000, 2)
        status = getattr(response, 'status_code', 0)

        # Direct logging
        success = log_request_direct(
            request_id=request_id,
            endpoint=str(request.url),
            method=request.method,
            path=request.url.path,
            response=response,
            response_body=response_body,
            status_code=status,
            client_ip=client_ip,
            user_agent=request.headers.get('user-agent'),
            request_query_params=dict(request.query_params),
            request_body=request_body,
            request_headers=request_headers,
            execution_time_ms=duration,
            error_message=error,
        )

        if not success:
            # Fallback to async factory logging
            log_entry = AppRequestLog(
                request_id=request_id,
                endpoint=str(request.url),
                method=request.method,
                client_ip=client_ip,
                user_agent=request.headers.get('user-agent'),
                user_id=getattr(request.state, 'user_id', None),
                request_path=request.url.path,
                request_query_params=dict(request.query_params),
                request_body=request_body,
                request_headers=request_headers,
                response_body=response_body,
                response_headers=dict(response.headers),
                status_code=status,
                execution_time_ms=duration,
                error_message=error,
                timestamp=datetime.utcnow(),
            )
            try:
                self.logger_factory.log_app_request(log_entry)
            except Exception as log_exc:
                logger.error(f"Logging failed: {log_exc}")

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
