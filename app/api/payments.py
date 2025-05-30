"""
Payment API endpoints for Razorpay eMandate integration
Handles customer onboarding, mandate management, and payment processing
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.common.response import ResponseUtil
from app.common.exceptions import ExternalAPIException, ValidationException
from app.db.session import get_db
from app.models.payment import MandateStatus, PaymentStatus
from app.models.user import User
from app.schemas.payment import (
    CustomerCreate, CustomerResponse, MandateCreate, MandateResponse,
    RecurringPaymentCreate, PaymentResponse, PaymentStatsResponse,
    PaymentFilter, MandateFilter, PaymentListResponse, MandateListResponse
)
from app.services.payment_service import get_payment_service
from app.utils.logger import logger

router = APIRouter(prefix="/payments", tags=["Payments"])

# Get payment service
payment_service = get_payment_service()


# === CUSTOMER ENDPOINTS ===

@router.post("/customers", response_model=CustomerResponse)
async def create_customer(
    customer_data: CustomerCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or get Razorpay customer for the current user"""
    
    try:
        logger.info(
            f"Creating customer for user {current_user.id}",
            extra={
                "event_type": "customer_creation_request",
                "user_id": current_user.id,
                "email": customer_data.email
            }
        )
        
        customer, created = await payment_service.create_or_get_customer(
            db=db,
            user=current_user,
            customer_data=customer_data
        )
        
        message = "Customer created successfully" if created else "Customer already exists"
        
        return ResponseUtil.success_response(
            data=CustomerResponse.from_orm(customer),
            message=message
        )
        
    except ExternalAPIException as e:
        logger.error(f"Razorpay API error in customer creation: {e}")
        return ResponseUtil.error_response(
            message="Failed to create customer",
            errors=[str(e)],
            status_code=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        logger.error(f"Unexpected error in customer creation: {e}")
        return ResponseUtil.error_response(
            message="Internal server error",
            errors=["An unexpected error occurred"],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/customers/me", response_model=CustomerResponse)
async def get_my_customer(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get customer details for the current user"""
    
    try:
        customer = await payment_service.get_customer_by_user(db, current_user.id)
        
        if not customer:
            return ResponseUtil.error_response(
                message="Customer not found",
                errors=["No customer profile found for this user"],
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return ResponseUtil.success_response(
            data=CustomerResponse.from_orm(customer),
            message="Customer details retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving customer: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve customer details",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# === MANDATE ENDPOINTS ===

@router.post("/mandates", response_model=MandateResponse)
async def create_mandate(
    mandate_request: MandateCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new eMandate for recurring payments"""
    
    try:
        logger.info(
            f"Creating mandate for user {current_user.id}",
            extra={
                "event_type": "mandate_creation_request",
                "user_id": current_user.id,
                "amount": mandate_request.amount,
                "frequency": mandate_request.frequency
            }
        )
        
        mandate = await payment_service.create_mandate(
            db=db,
            user=current_user,
            mandate_data=mandate_request
        )
        
        return ResponseUtil.success_response(
            data=mandate,
            message="Mandate created successfully"
        )
        
    except ValidationException as e:
        logger.error(f"Validation error in mandate creation: {e}")
        return ResponseUtil.error_response(
            message="Validation failed",
            errors=[str(e)],
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except ExternalAPIException as e:
        logger.error(f"Razorpay API error in mandate creation: {e}")
        return ResponseUtil.error_response(
            message="Failed to create mandate",
            errors=[str(e)],
            status_code=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        logger.error(f"Unexpected error in mandate creation: {e}")
        return ResponseUtil.error_response(
            message="Internal server error",
            errors=["An unexpected error occurred"],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/mandates/{mandate_id}", response_model=MandateResponse)
async def get_mandate(
    mandate_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get mandate details by ID"""
    
    try:
        mandate = await payment_service.get_mandate_by_id(db, mandate_id, current_user.id)
        
        if not mandate:
            return ResponseUtil.error_response(
                message="Mandate not found",
                errors=[f"Mandate with ID {mandate_id} not found"],
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return ResponseUtil.success_response(
            data=MandateResponse.from_orm(mandate),
            message="Mandate details retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving mandate: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve mandate details",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/mandates", response_model=MandateListResponse)
async def list_my_mandates(
    status: Optional[MandateStatus] = None,
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List mandates for the current user"""
    
    try:
        mandates = await payment_service.get_user_mandates(
            db, current_user.id, status, skip, limit
        )
        
        mandate_responses = [MandateResponse.from_orm(mandate) for mandate in mandates]
        
        response_data = MandateListResponse(
            mandates=mandate_responses,
            total=len(mandate_responses),
            skip=skip,
            limit=limit,
            has_more=len(mandate_responses) == limit
        )
        
        return ResponseUtil.success_response(
            data=response_data,
            message="Mandates retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error listing mandates: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve mandates",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# === PAYMENT ENDPOINTS ===

@router.post("/mandates/{mandate_id}/charge", response_model=PaymentResponse)
async def create_recurring_payment(
    mandate_id: int,
    payment_request: RecurringPaymentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a recurring payment using an existing mandate"""
    
    try:
        # Set mandate_id from URL parameter
        payment_request.mandate_id = mandate_id
        
        logger.info(
            f"Creating recurring payment for user {current_user.id}",
            extra={
                "event_type": "recurring_payment_request",
                "user_id": current_user.id,
                "mandate_id": mandate_id,
                "amount": payment_request.amount
            }
        )
        
        payment = await payment_service.create_recurring_payment(
            db=db,
            user=current_user,
            payment_data=payment_request
        )
        
        return ResponseUtil.success_response(
            data=payment,
            message="Recurring payment initiated successfully"
        )
        
    except ValidationException as e:
        logger.error(f"Validation error in recurring payment: {e}")
        return ResponseUtil.error_response(
            message="Validation failed",
            errors=[str(e)],
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except ExternalAPIException as e:
        logger.error(f"Razorpay API error in recurring payment: {e}")
        return ResponseUtil.error_response(
            message="Failed to create recurring payment",
            errors=[str(e)],
            status_code=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        logger.error(f"Unexpected error in recurring payment: {e}")
        return ResponseUtil.error_response(
            message="Internal server error",
            errors=["An unexpected error occurred"],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/transactions/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment transaction details by ID"""
    
    try:
        payment = await payment_service.get_payment_by_id(db, payment_id, current_user.id)
        
        if not payment:
            return ResponseUtil.error_response(
                message="Payment not found",
                errors=[f"Payment with ID {payment_id} not found"],
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return ResponseUtil.success_response(
            data=PaymentResponse.from_orm(payment),
            message="Payment details retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving payment: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve payment details",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/transactions", response_model=PaymentListResponse)
async def list_my_payments(
    status: Optional[PaymentStatus] = None,
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List payment transactions for the current user"""
    
    try:
        payments = await payment_service.get_user_payments(
            db, current_user.id, status, skip, limit
        )
        
        payment_responses = [PaymentResponse.from_orm(payment) for payment in payments]
        
        response_data = PaymentListResponse(
            payments=payment_responses,
            total=len(payment_responses),
            skip=skip,
            limit=limit,
            has_more=len(payment_responses) == limit
        )
        
        return ResponseUtil.success_response(
            data=response_data,
            message="Payments retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error listing payments: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve payments",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/stats", response_model=PaymentStatsResponse)
async def get_payment_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment statistics for the current user"""
    
    try:
        stats = await payment_service.get_payment_statistics(db, current_user.id)
        
        return ResponseUtil.success_response(
            data=PaymentStatsResponse(**stats),
            message="Payment statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error retrieving payment stats: {e}")
        return ResponseUtil.error_response(
            message="Failed to retrieve payment statistics",
            errors=[str(e)],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# === WEBHOOK ENDPOINT ===

@router.post("/webhooks")
async def handle_razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Razorpay webhook events"""
    
    try:
        # Get raw body and signature
        raw_body = await request.body()
        signature = request.headers.get("X-Razorpay-Signature")
        
        if not signature:
            logger.warning("Webhook received without signature")
            return ResponseUtil.error_response(
                message="Missing webhook signature",
                errors=["X-Razorpay-Signature header required"],
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse JSON payload
        try:
            payload = json.loads(raw_body.decode())
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return ResponseUtil.error_response(
                message="Invalid JSON payload",
                errors=["Webhook payload must be valid JSON"],
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(
            f"Processing webhook: {payload.get('event')}",
            extra={
                "event_type": "webhook_received",
                "webhook_event": payload.get("event"),
                "entity_id": payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
            }
        )
        
        # Process webhook
        success = await payment_service.process_webhook_event(
            db=db,
            event_data=payload,
            signature=signature,
            raw_payload=raw_body.decode()
        )
        
        if success:
            return JSONResponse(
                content={"status": "success", "message": "Webhook processed successfully"},
                status_code=200
            )
        else:
            return JSONResponse(
                content={"status": "error", "message": "Failed to process webhook"},
                status_code=400
            )
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return JSONResponse(
            content={"status": "error", "message": "Internal server error"},
            status_code=500
        ) 