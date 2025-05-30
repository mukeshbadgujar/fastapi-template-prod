import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel
from sqlalchemy import desc, select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.common.response import ResponseUtil
from app.config.settings import settings
from app.core.logging_backend import APIRequestLog, get_db_logger
from app.db.session import get_db
from app.models.user import User
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


# === PAYMENT ADMIN ENDPOINTS ===

@router.get("/payments/stats")
async def get_payment_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive payment statistics for admin monitoring"""
    
    try:
        from app.services.payment_service import get_payment_service
        
        payment_service = get_payment_service()
        stats = await payment_service.get_payment_statistics(db)
        
        return ResponseUtil.success_response(
            data=stats,
            message="Payment statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving payment statistics: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve payment statistics",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/payments/mandates")
async def list_all_mandates(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all mandates for admin monitoring"""
    
    try:
        from app.models.payment import Mandate, RazorpayCustomer, MandateStatus
        from app.schemas.payment import MandateResponse
        from sqlalchemy.orm import selectinload
        
        stmt = select(Mandate).options(
            selectinload(Mandate.customer)
        ).join(RazorpayCustomer)
        
        if status:
            try:
                mandate_status = MandateStatus(status)
                stmt = stmt.where(Mandate.status == mandate_status)
            except ValueError:
                return ResponseUtil.error_response(
                    message="Invalid status",
                    errors=[f"Status must be one of: {[s.value for s in MandateStatus]}"],
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        stmt = stmt.order_by(desc(Mandate.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        mandates = result.scalars().all()
        
        mandate_responses = [MandateResponse.from_orm(mandate) for mandate in mandates]
        
        return ResponseUtil.success_response(
            data={
                "mandates": mandate_responses,
                "total": len(mandate_responses),
                "skip": skip,
                "limit": limit,
                "has_more": len(mandate_responses) == limit
            },
            message="Mandates retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error listing mandates: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve mandates",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/payments/failed")
async def get_failed_payments(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get failed payments for admin analysis"""
    
    try:
        from app.models.payment import PaymentTransaction, RazorpayCustomer, PaymentStatus
        from app.schemas.payment import PaymentResponse
        from sqlalchemy.orm import selectinload
        
        stmt = select(PaymentTransaction).options(
            selectinload(PaymentTransaction.customer),
            selectinload(PaymentTransaction.mandate)
        ).join(RazorpayCustomer).where(
            PaymentTransaction.status == PaymentStatus.FAILED
        ).order_by(desc(PaymentTransaction.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        payments = result.scalars().all()
        
        payment_responses = []
        for payment in payments:
            payment_data = PaymentResponse.from_orm(payment)
            payment_responses.append(payment_data)
        
        return ResponseUtil.success_response(
            data={
                "failed_payments": payment_responses,
                "total": len(payment_responses),
                "skip": skip,
                "limit": limit,
                "has_more": len(payment_responses) == limit
            },
            message="Failed payments retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving failed payments: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve failed payments",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/webhooks/events")
async def list_webhook_events(
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List webhook events for admin monitoring"""
    
    try:
        from app.models.payment import WebhookEvent, WebhookEventStatus
        from app.schemas.payment import WebhookEventResponse
        
        stmt = select(WebhookEvent)
        
        if event_type:
            stmt = stmt.where(WebhookEvent.event_type == event_type)
        
        if status:
            try:
                webhook_status = WebhookEventStatus(status)
                stmt = stmt.where(WebhookEvent.status == webhook_status)
            except ValueError:
                return ResponseUtil.error_response(
                    message="Invalid status",
                    errors=[f"Status must be one of: {[s.value for s in WebhookEventStatus]}"],
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        stmt = stmt.order_by(desc(WebhookEvent.received_at)).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        events = result.scalars().all()
        
        event_responses = [WebhookEventResponse.from_orm(event) for event in events]
        
        return ResponseUtil.success_response(
            data={
                "webhook_events": event_responses,
                "total": len(event_responses),
                "skip": skip,
                "limit": limit,
                "has_more": len(event_responses) == limit
            },
            message="Webhook events retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error listing webhook events: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve webhook events",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/payments/customers")
async def list_payment_customers(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List payment customers for admin monitoring"""
    
    try:
        from app.models.payment import RazorpayCustomer
        from app.schemas.payment import CustomerResponse
        from sqlalchemy.orm import selectinload
        
        stmt = select(RazorpayCustomer).options(
            selectinload(RazorpayCustomer.user)
        ).order_by(desc(RazorpayCustomer.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(stmt)
        customers = result.scalars().all()
        
        customer_responses = [CustomerResponse.from_orm(customer) for customer in customers]
        
        return ResponseUtil.success_response(
            data={
                "customers": customer_responses,
                "total": len(customer_responses),
                "skip": skip,
                "limit": limit,
                "has_more": len(customer_responses) == limit
            },
            message="Payment customers retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error listing payment customers: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve payment customers",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# === PAYMENT ANALYTICS ENDPOINT ===

@router.get("/analytics/payments")
async def get_payment_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment analytics for specified number of days"""
    
    try:
        from app.models.payment import PaymentTransaction, PaymentStatus
        from datetime import datetime, timedelta
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Daily payment counts and amounts
        daily_stats_stmt = select(
            func.date(PaymentTransaction.created_at).label('date'),
            func.count(PaymentTransaction.id).label('count'),
            func.sum(PaymentTransaction.amount).label('amount'),
            func.count(
                case(
                    (PaymentTransaction.status == PaymentStatus.CAPTURED, 1),
                    else_=None
                )
            ).label('successful_count'),
            func.count(
                case(
                    (PaymentTransaction.status == PaymentStatus.FAILED, 1),
                    else_=None
                )
            ).label('failed_count')
        ).where(
            PaymentTransaction.created_at >= start_date
        ).group_by(
            func.date(PaymentTransaction.created_at)
        ).order_by(
            func.date(PaymentTransaction.created_at)
        )
        
        result = await db.execute(daily_stats_stmt)
        daily_stats = result.all()
        
        # Payment method breakdown
        method_stats_stmt = select(
            PaymentTransaction.method,
            func.count(PaymentTransaction.id).label('count'),
            func.sum(PaymentTransaction.amount).label('amount')
        ).where(
            PaymentTransaction.created_at >= start_date
        ).group_by(
            PaymentTransaction.method
        )
        
        method_result = await db.execute(method_stats_stmt)
        method_stats = method_result.all()
        
        analytics_data = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "daily_stats": [
                {
                    "date": stat.date.isoformat(),
                    "total_payments": stat.count,
                    "total_amount": stat.amount or 0,
                    "successful_payments": stat.successful_count,
                    "failed_payments": stat.failed_count
                }
                for stat in daily_stats
            ],
            "method_breakdown": [
                {
                    "method": stat.method,
                    "count": stat.count,
                    "amount": stat.amount or 0
                }
                for stat in method_stats
            ]
        }
        
        return ResponseUtil.success_response(
            data=analytics_data,
            message="Payment analytics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving payment analytics: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve payment analytics",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
