"""
SQLAlchemy models for Razorpay payment operations
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, Boolean, Numeric
from sqlalchemy.orm import relationship

from app.models.base import Base


class MandateStatus(str, Enum):
    """eMandate status enumeration"""
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    CREATED = "created"
    CAPTURED = "captured"
    AUTHORIZED = "authorized"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class WebhookEventStatus(str, Enum):
    """Webhook event processing status"""
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    IGNORED = "ignored"


class RazorpayCustomer(Base):
    """
    Razorpay customer profiles linked to application users
    """
    __tablename__ = "razorpay_customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    razorpay_customer_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Customer details
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    contact = Column(String(20), nullable=False)
    
    # Additional customer data
    gstin = Column(String(20), nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="razorpay_customer")
    mandates = relationship("Mandate", back_populates="customer", cascade="all, delete-orphan")
    payments = relationship("PaymentTransaction", back_populates="customer")

    def __repr__(self):
        return f"<RazorpayCustomer(id={self.id}, email='{self.email}', rzp_id='{self.razorpay_customer_id}')>"


class Mandate(Base):
    """
    eMandate records for recurring payments
    """
    __tablename__ = "mandates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("razorpay_customers.id"), nullable=False)
    
    # Razorpay identifiers
    razorpay_payment_id = Column(String(255), unique=True, nullable=False, index=True)
    razorpay_order_id = Column(String(255), nullable=False, index=True)
    token_id = Column(String(255), nullable=True, index=True)  # Available after successful registration
    
    # Mandate details
    amount = Column(Integer, nullable=False)  # Amount in smallest currency unit (paise)
    currency = Column(String(3), default="INR", nullable=False)
    max_amount = Column(Integer, nullable=True)  # Maximum debit amount
    
    # Bank account details
    bank_account_number = Column(String(50), nullable=True)
    bank_ifsc = Column(String(20), nullable=True)
    bank_name = Column(String(255), nullable=True)
    
    # Mandate configuration
    method = Column(String(50), default="emandate", nullable=False)
    description = Column(Text, nullable=True)
    frequency = Column(String(50), nullable=True)  # monthly, quarterly, yearly, etc.
    
    # Status tracking
    status = Column(SQLEnum(MandateStatus), default=MandateStatus.CREATED, nullable=False)
    
    # Dates
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Metadata
    notes = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("RazorpayCustomer", back_populates="mandates")
    payments = relationship("PaymentTransaction", back_populates="mandate")

    def __repr__(self):
        return f"<Mandate(id={self.id}, payment_id='{self.razorpay_payment_id}', status='{self.status}')>"


class PaymentTransaction(Base):
    """
    Individual payment transaction records
    """
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("razorpay_customers.id"), nullable=False)
    mandate_id = Column(Integer, ForeignKey("mandates.id"), nullable=True)  # NULL for one-time payments
    
    # Razorpay identifiers
    razorpay_payment_id = Column(String(255), unique=True, nullable=False, index=True)
    razorpay_order_id = Column(String(255), nullable=True, index=True)
    
    # Payment details
    amount = Column(Integer, nullable=False)  # Amount in smallest currency unit
    currency = Column(String(3), default="INR", nullable=False)
    method = Column(String(50), nullable=False)  # emandate, netbanking, card, etc.
    
    # Status and processing
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.CREATED, nullable=False)
    captured_amount = Column(Integer, default=0, nullable=False)
    
    # Transaction details
    description = Column(Text, nullable=True)
    receipt = Column(String(255), nullable=True)
    
    # Bank/Gateway details
    bank = Column(String(100), nullable=True)
    acquirer_data = Column(Text, nullable=True)  # JSON string
    
    # Error handling
    error_code = Column(String(100), nullable=True)
    error_description = Column(Text, nullable=True)
    error_source = Column(String(100), nullable=True)
    error_step = Column(String(100), nullable=True)
    error_reason = Column(String(100), nullable=True)
    
    # Fees and taxes
    fee = Column(Integer, default=0, nullable=False)
    tax = Column(Integer, default=0, nullable=False)
    
    # Metadata
    notes = Column(Text, nullable=True)
    
    # Timestamps
    authorized_at = Column(DateTime, nullable=True)
    captured_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("RazorpayCustomer", back_populates="payments")
    mandate = relationship("Mandate", back_populates="payments")

    def __repr__(self):
        return f"<PaymentTransaction(id={self.id}, payment_id='{self.razorpay_payment_id}', status='{self.status}')>"


class WebhookEvent(Base):
    """
    Razorpay webhook event logging and processing
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Event identifiers
    razorpay_event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # payment.captured, payment.failed, etc.
    
    # Related entities
    entity_id = Column(String(255), nullable=False, index=True)  # payment_id, order_id, etc.
    entity_type = Column(String(50), nullable=False)  # payment, order, subscription, etc.
    
    # Event data
    payload = Column(Text, nullable=False)  # Full JSON payload
    signature = Column(String(255), nullable=False)
    
    # Processing status
    status = Column(SQLEnum(WebhookEventStatus), default=WebhookEventStatus.PENDING, nullable=False)
    processing_attempts = Column(Integer, default=0, nullable=False)
    
    # Processing results
    processing_error = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    event_created_at = Column(DateTime, nullable=False)  # From Razorpay event
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, event_type='{self.event_type}', status='{self.status}')>"


class PaymentRefund(Base):
    """
    Payment refund records
    """
    __tablename__ = "payment_refunds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_transaction_id = Column(Integer, ForeignKey("payment_transactions.id"), nullable=False)
    
    # Razorpay identifiers
    razorpay_refund_id = Column(String(255), unique=True, nullable=False, index=True)
    razorpay_payment_id = Column(String(255), nullable=False, index=True)
    
    # Refund details
    amount = Column(Integer, nullable=False)  # Refund amount in smallest currency unit
    currency = Column(String(3), default="INR", nullable=False)
    
    # Status and metadata
    status = Column(String(50), nullable=False)  # processed, pending, failed
    receipt = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Processing details
    speed = Column(String(20), nullable=True)  # normal, optimum
    batch_id = Column(String(255), nullable=True)
    
    # Timestamps
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    payment_transaction = relationship("PaymentTransaction")

    def __repr__(self):
        return f"<PaymentRefund(id={self.id}, refund_id='{self.razorpay_refund_id}', amount={self.amount})>" 