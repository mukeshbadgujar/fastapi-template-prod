import json
import time
import uuid
import traceback
from datetime import datetime

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.common.models import AppRequestLog
from app.common.db_logging.factory import DBLoggerFactory, global_logger_factory
from app.config.settings import settings
from app.utils.direct_logger import log_request_direct, ensure_sqlite_table_exists
from app.utils.logger import logger

# Ensure SQLite table exists
enabled = ensure_sqlite_table_exists()
if not enabled:
    logger.warning("Failed to init SQLite table for API logs.")

class RequestLoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger_factory = global_logger_factory
        self.real_time = settings.API_LOG_REAL_TIME

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract request data
        start = time.time()
        client_ip = request.client.host if request.client else None
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("authorization", "cookie")}
        body = None
        try:
            raw = await request.body()
            if raw:
                body = json.loads(raw)
        except Exception:
            body = {"raw": raw.decode(errors="ignore")} if raw else None

        # Call downstream
        try:
            response = await call_next(request)
        except Exception as exc:
            response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
            error = str(exc)
            tb = traceback.format_exc()
            self._log(request_id, request, response, start, body, client_ip, headers, error)
            raise

        # Attach headers
        exec_ms = round((time.time() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{exec_ms}ms"

        # Log
        self._log(request_id, request, response, start, body, client_ip, headers)
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
        error: str = None,
    ):
        duration = round((time.time() - start) * 1000, 2)
        status = response.status_code if hasattr(response, "status_code") else 0

        # Try to fetch response body if small
        resp_body = None
        try:
            if hasattr(response, "body"):
                raw = response.body
                text = raw.decode(errors="ignore")
                resp_body = json.loads(text)
        except Exception:
            resp_body = None

        # Direct logging
        success = log_request_direct(
            request_id=request_id,
            endpoint=str(request.url),
            method=request.method,
            path=request.url.path,
            response=response,
            status_code=status,
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
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
                user_agent=request.headers.get("user-agent"),
                user_id=getattr(request.state, "user_id", None),
                request_path=request.url.path,
                request_query_params=dict(request.query_params),
                request_body=request_body,
                request_headers=request_headers,
                response_body=resp_body,
                response_headers=dict(response.headers),
                status_code=status,
                execution_time_ms=duration,
                error_message=error,
                timestamp=datetime.utcnow(),
            )
            try:
                # fire-and-forget
                self.logger_factory.log_app_request(log_entry)
            except Exception as log_exc:
                logger.error(f"Logging failed: {log_exc}")

