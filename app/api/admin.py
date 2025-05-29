import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config.settings import settings
from app.utils.direct_logger import SQLITE_DB_PATH, get_app_request_logs
from app.utils.logger import logger

# Create admin router
router = APIRouter(prefix="/admin", tags=["Admin"])


class RequestLog(BaseModel):
    """Request log model for response"""
    request_id: str
    endpoint: str
    method: str
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_path: str
    request_query_params: Dict[str, Any] = {}
    status_code: int
    execution_time_ms: float
    error_message: Optional[str] = None
    timestamp: str


class RequestLogDetail(RequestLog):
    """Request log with full detail including bodies"""
    request_body: Optional[Dict[str, Any]] = None
    response_body: Optional[Dict[str, Any]] = None


@router.get("/logs/requests", response_model=List[RequestLog])
async def get_request_logs(
    limit: int = Query(10, description="Maximum number of logs to retrieve", ge=1, le=100),
    refresh: bool = Query(True, description="Whether to refresh the connection to get the latest logs")
):
    """
    Get the most recent application request logs.

    This endpoint provides access to the request logs stored in the SQLite database.
    It's useful for debugging and monitoring API activity.
    """
    try:
        # Always convert limit to int from query parameter
        limit_value = int(limit)
        logs = get_app_request_logs(limit=limit_value, with_body=False, refresh=refresh)
        return logs
    except Exception as e:
        logger.error(f"Error retrieving request logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.get("/logs/requests/{request_id}", response_model=RequestLogDetail)
async def get_request_log_detail(request_id: str):
    """
    Get detailed information about a specific request including request and response bodies.

    This endpoint is useful for debugging specific API calls by request ID.
    """
    try:
        # Get log with bodies included
        logs = get_app_request_logs(limit=1000, with_body=True)

        # Find the specific request
        for log in logs:
            if log.get("request_id") == request_id:
                return log

        # If we get here, log was not found
        raise HTTPException(status_code=404, detail=f"Request log with ID {request_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving request log detail: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve log detail")


@router.get("/logs/db-info")
async def get_db_info():
    """
    Get information about the SQLite database configuration
    """
    return {
        "db_path": SQLITE_DB_PATH,
        "absolute_path": os.path.abspath(SQLITE_DB_PATH),
        "exists": os.path.exists(SQLITE_DB_PATH),
        "size_bytes": os.path.getsize(SQLITE_DB_PATH) if os.path.exists(SQLITE_DB_PATH) else 0,
        "settings_path": settings.API_LOG_SQLITE_PATH
    }


@router.post("/logs/toggle-real-time")
async def toggle_real_time_logging(enable: bool = Query(None, description="Enable or disable real-time logging")):
    """
    Toggle real-time request logging

    This endpoint allows you to enable or disable real-time request logging.
    When disabled, requests will not be logged to the SQLite database in real-time,
    which can improve performance in high-traffic environments.
    """
    # Import the module with the global variable
    from app.middleware.request_logger import REAL_TIME_LOGGING

    # Get the current value if no parameter specified
    if enable is None:
        return {"real_time_logging": REAL_TIME_LOGGING}

    # Update the module's global variable
    import sys
    module = sys.modules['app.middleware.request_logger']
    setattr(module, 'REAL_TIME_LOGGING', enable)

    return {
        "real_time_logging": enable,
        "message": f"Real-time logging {'enabled' if enable else 'disabled'}"
    }
