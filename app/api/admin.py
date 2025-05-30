import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select

from app.config.settings import settings
from app.core.logging_backend import APIRequestLog, get_db_logger
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

    This endpoint provides access to the request logs stored in the database.
    It's useful for debugging and monitoring API activity.
    """
    try:
        db_logger = await get_db_logger()
        if not db_logger:
            raise HTTPException(status_code=503, detail="Logging backend not available")

        # Get logs from database
        async with db_logger.async_session_maker() as session:
            result = await session.execute(
                select(APIRequestLog)
                .order_by(desc(APIRequestLog.timestamp))
                .limit(limit)
            )
            logs = result.scalars().all()

            return [
                RequestLog(
                    request_id=log.request_id or "",
                    endpoint=log.path or "",
                    method=log.method or "",
                    client_ip=log.client_ip,
                    user_agent=log.user_agent,
                    request_path=log.path or "",
                    request_query_params=log.query_params or {},
                    status_code=log.status_code or 0,
                    execution_time_ms=log.execution_time_ms or 0.0,
                    error_message=log.error_message,
                    timestamp=log.timestamp.isoformat() if log.timestamp else ""
                )
                for log in logs
            ]

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
        db_logger = await get_db_logger()
        if not db_logger:
            raise HTTPException(status_code=503, detail="Logging backend not available")

        # Get specific log from database
        async with db_logger.async_session_maker() as session:
            result = await session.execute(
                select(APIRequestLog).where(APIRequestLog.request_id == request_id)
            )
            log = result.scalar_one_or_none()

            if not log:
                raise HTTPException(status_code=404, detail=f"Request log with ID {request_id} not found")

            return RequestLogDetail(
                request_id=log.request_id or "",
                endpoint=log.path or "",
                method=log.method or "",
                client_ip=log.client_ip,
                user_agent=log.user_agent,
                request_path=log.path or "",
                request_query_params=log.query_params or {},
                status_code=log.status_code or 0,
                execution_time_ms=log.execution_time_ms or 0.0,
                error_message=log.error_message,
                timestamp=log.timestamp.isoformat() if log.timestamp else "",
                request_body=log.body,
                response_body=log.response_body
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving request log detail: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve log detail")


@router.get("/logs/db-info")
async def get_db_info():
    """
    Get information about the logging database configuration
    """
    db_logger = await get_db_logger()
    
    return {
        "log_db_url": settings.LOG_DB_URL,
        "api_log_table": settings.API_LOG_TABLE,
        "internal_api_log_table": settings.INT_API_LOG_TABLE,
        "backend_available": db_logger is not None,
        "backend_initialized": db_logger._initialized if db_logger else False
    }


@router.get("/logs/stats")
async def get_log_stats():
    """
    Get statistics about the logs in the database
    """
    try:
        db_logger = await get_db_logger()
        if not db_logger:
            raise HTTPException(status_code=503, detail="Logging backend not available")

        async with db_logger.async_session_maker() as session:
            # Count total logs
            from sqlalchemy import func
            total_logs = await session.scalar(select(func.count(APIRequestLog.id)))
            
            # Count by status code
            status_counts = await session.execute(
                select(APIRequestLog.status_code, func.count(APIRequestLog.id))
                .group_by(APIRequestLog.status_code)
                .order_by(APIRequestLog.status_code)
            )
            
            return {
                "total_logs": total_logs,
                "status_code_distribution": {
                    str(status): count for status, count in status_counts.all()
                }
            }

    except Exception as e:
        logger.error(f"Error retrieving log stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve log statistics")
