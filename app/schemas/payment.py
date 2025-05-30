"""
Pydantic schemas for Razorpay payment operations
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum

from pydantic import BaseModel, Field, validator, EmailStr

from app.models.payment import MandateStatus, PaymentStatus, WebhookEventStatus


# === BASE SCHEMAS ===

class PaymentBase(BaseModel):
    """Base payment schema"""
    amount: int = Field(..., description="Amount in smallest currency unit (paise for INR)", gt=0)
    currency: str = Field("INR", description="Currency code")
    description: Optional[str] = Field(None, description="Payment description")


class CustomerBase(BaseModel):
    """Base customer schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Customer full name")
    email: EmailStr = Field(..., description="Customer email address")
    contact: str = Field(..., description="Customer phone number")
    
    @validator('contact')
    def validate_contact(cls, v):
        """Validate phone number format"""
        # Remove any non-digit characters for validation
        digits_only = ''.join(filter(str.isdigit, v))
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Contact number must be between 10 and 15 digits')
        return v


# === CUSTOMER SCHEMAS ===

class CustomerCreate(CustomerBase):
    """Schema for creating a customer"""
    gstin: Optional[str] = Field(None, description="GST identification number")
    notes: Optional[str] = Field(None, description="Additional notes")
    fail_existing: bool = Field(False, description="Whether to fail if customer already exists")


class CustomerUpdate(BaseModel):
    """Schema for updating customer details"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    contact: Optional[str] = None
    gstin: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    """Schema for customer response"""
    id: int
    user_id: int
    razorpay_customer_id: str
    gstin: Optional[str]
    is_active: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === MANDATE SCHEMAS ===

class BankAccountDetails(BaseModel):
    """Bank account details for eMandate"""
    account_number: str = Field(..., description="Bank account number")
    ifsc: str = Field(..., description="Bank IFSC code")
    name: Optional[str] = Field(None, description="Bank name")


class MandateCreate(PaymentBase):
    """Schema for creating an eMandate"""
    customer_id: Optional[int] = Field(None, description="Internal customer ID")
    max_amount: Optional[int] = Field(None, description="Maximum debit amount")
    frequency: Optional[str] = Field(None, description="Frequency of payments")
    start_date: Optional[datetime] = Field(None, description="Mandate start date")
    end_date: Optional[datetime] = Field(None, description="Mandate end date")
    bank_account: Optional[BankAccountDetails] = Field(None, description="Bank account details")
    notes: Optional[str] = Field(None, description="Additional notes")

    @validator('end_date')
    def validate_end_date(cls, v, values):
        """Ensure end date is after start date"""
        if v and 'start_date' in values and values['start_date']:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v


class MandateUpdate(BaseModel):
    """Schema for updating mandate"""
    max_amount: Optional[int] = None
    frequency: Optional[str] = None
    end_date: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[MandateStatus] = None


class MandateResponse(BaseModel):
    """Schema for mandate response"""
    id: int
    customer_id: int
    razorpay_payment_id: str
    razorpay_order_id: str
    token_id: Optional[str]
    amount: int
    currency: str
    max_amount: Optional[int]
    bank_account_number: Optional[str]
    bank_ifsc: Optional[str]
    bank_name: Optional[str]
    method: str
    description: Optional[str]
    frequency: Optional[str]
    status: MandateStatus
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    notes: Optional[str]
    failure_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Related data
    customer: Optional[CustomerResponse] = None

    class Config:
        from_attributes = True


# === PAYMENT TRANSACTION SCHEMAS ===

class PaymentCreate(PaymentBase):
    """Schema for creating a payment"""
    customer_id: Optional[int] = Field(None, description="Internal customer ID")
    mandate_id: Optional[int] = Field(None, description="Mandate ID for recurring payments")
    method: str = Field(..., description="Payment method")
    receipt: Optional[str] = Field(None, description="Receipt identifier")
    notes: Optional[str] = Field(None, description="Payment notes")


class RecurringPaymentCreate(BaseModel):
    """Schema for creating recurring payment"""
    amount: int = Field(..., description="Amount to charge", gt=0)
    mandate_id: int = Field(..., description="Mandate ID to use for payment")
    description: Optional[str] = Field(None, description="Payment description")
    receipt: Optional[str] = Field(None, description="Receipt identifier")
    notes: Optional[str] = Field(None, description="Payment notes")


class PaymentCaptureRequest(BaseModel):
    """Schema for capturing a payment"""
    amount: int = Field(..., description="Amount to capture", gt=0)


class PaymentResponse(BaseModel):
    """Schema for payment response"""
    id: int
    customer_id: int
    mandate_id: Optional[int]
    razorpay_payment_id: str
    razorpay_order_id: Optional[str]
    amount: int
    currency: str
    method: str
    status: PaymentStatus
    captured_amount: int
    description: Optional[str]
    receipt: Optional[str]
    bank: Optional[str]
    error_code: Optional[str]
    error_description: Optional[str]
    fee: int
    tax: int
    notes: Optional[str]
    authorized_at: Optional[datetime]
    captured_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Related data
    customer: Optional[CustomerResponse] = None
    mandate: Optional[MandateResponse] = None

    class Config:
        from_attributes = True


# === WEBHOOK SCHEMAS ===

class WebhookEventCreate(BaseModel):
    """Schema for creating webhook event"""
    razorpay_event_id: str
    event_type: str
    entity_id: str
    entity_type: str
    payload: str  # JSON string
    signature: str
    event_created_at: datetime


class WebhookEventResponse(BaseModel):
    """Schema for webhook event response"""
    id: int
    razorpay_event_id: str
    event_type: str
    entity_id: str
    entity_type: str
    status: WebhookEventStatus
    processing_attempts: int
    processing_error: Optional[str]
    processed_at: Optional[datetime]
    event_created_at: datetime
    received_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === REFUND SCHEMAS ===

class RefundCreate(BaseModel):
    """Schema for creating a refund"""
    payment_id: str = Field(..., description="Razorpay payment ID")
    amount: Optional[int] = Field(None, description="Refund amount (full refund if not specified)")
    speed: Optional[str] = Field("normal", description="Refund speed: normal or optimum")
    notes: Optional[str] = Field(None, description="Refund notes")
    receipt: Optional[str] = Field(None, description="Receipt identifier")


class RefundResponse(BaseModel):
    """Schema for refund response"""
    id: int
    payment_transaction_id: int
    razorpay_refund_id: str
    razorpay_payment_id: str
    amount: int
    currency: str
    status: str
    receipt: Optional[str]
    notes: Optional[str]
    speed: Optional[str]
    batch_id: Optional[str]
    processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === REPORTING SCHEMAS ===

class PaymentStatsResponse(BaseModel):
    """Schema for payment statistics"""
    total_payments: int = Field(..., description="Total number of payments")
    total_amount: int = Field(..., description="Total payment amount")
    successful_payments: int = Field(..., description="Number of successful payments")
    failed_payments: int = Field(..., description="Number of failed payments")
    pending_payments: int = Field(..., description="Number of pending payments")
    total_refunds: int = Field(..., description="Total refund amount")
    active_mandates: int = Field(..., description="Number of active mandates")
    total_customers: int = Field(..., description="Total number of customers")


class PaymentFilter(BaseModel):
    """Schema for payment filtering"""
    customer_id: Optional[int] = None
    mandate_id: Optional[int] = None
    status: Optional[PaymentStatus] = None
    method: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    min_amount: Optional[int] = None
    max_amount: Optional[int] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(10, ge=1, le=100)


class MandateFilter(BaseModel):
    """Schema for mandate filtering"""
    customer_id: Optional[int] = None
    status: Optional[MandateStatus] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(10, ge=1, le=100)


# === RAZORPAY WEBHOOK PAYLOAD SCHEMAS ===

class RazorpayEntity(BaseModel):
    """Base Razorpay entity"""
    id: str
    entity: str
    created_at: int  # Unix timestamp


class RazorpayPaymentEntity(RazorpayEntity):
    """Razorpay payment entity from webhook"""
    amount: int
    currency: str
    status: str
    method: Optional[str] = None
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    description: Optional[str] = None
    captured: bool = False
    fee: Optional[int] = None
    tax: Optional[int] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None


class RazorpayWebhookPayload(BaseModel):
    """Complete Razorpay webhook payload"""
    entity: str
    account_id: str
    event: str
    contains: List[str]
    payload: Dict[str, Any]
    created_at: int


# === COMBINED RESPONSE SCHEMAS ===

class PaymentListResponse(BaseModel):
    """Paginated payment list response"""
    payments: List[PaymentResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class MandateListResponse(BaseModel):
    """Paginated mandate list response"""
    mandates: List[MandateResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class CustomerListResponse(BaseModel):
    """Paginated customer list response"""
    customers: List[CustomerResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


# === ERROR SCHEMAS ===

class PaymentError(BaseModel):
    """Payment error details"""
    code: str
    description: str
    source: Optional[str] = None
    step: Optional[str] = None
    reason: Optional[str] = None


class PaymentErrorResponse(BaseModel):
    """Payment error response"""
    error: PaymentError
    payment_id: Optional[str] = None
    order_id: Optional[str] = None 