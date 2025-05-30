"""
Payment Service Layer for Razorpay eMandate Integration
Handles business logic for payments, mandates, and customer management
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

from app.integrations.razorpay_client import get_razorpay_client
from app.models.payment import (
    RazorpayCustomer, Mandate, PaymentTransaction, WebhookEvent, PaymentRefund,
    MandateStatus, PaymentStatus, WebhookEventStatus
)
from app.models.user import User
from app.schemas.payment import (
    CustomerCreate, CustomerResponse, MandateCreate, MandateResponse,
    PaymentCreate, PaymentResponse, RecurringPaymentCreate
)
from app.common.exceptions import ExternalAPIException, ValidationException
from app.utils.logger import logger


class PaymentService:
    """
    Service layer for payment operations
    """

    def __init__(self):
        self.razorpay_client = get_razorpay_client()

    # === CUSTOMER MANAGEMENT ===

    async def create_or_get_customer(
        self,
        db: AsyncSession,
        user: User,
        customer_data: CustomerCreate
    ) -> Tuple[RazorpayCustomer, bool]:
        """
        Create or get existing Razorpay customer for a user
        
        Returns:
            Tuple of (customer, created_flag)
        """
        try:
            # Check if customer already exists for this user
            stmt = select(RazorpayCustomer).where(RazorpayCustomer.user_id == user.id)
            result = await db.execute(stmt)
            existing_customer = result.scalar_one_or_none()

            if existing_customer:
                logger.info(
                    f"Using existing customer for user {user.id}",
                    extra={
                        "event_type": "existing_customer_found",
                        "user_id": user.id,
                        "customer_id": existing_customer.id
                    }
                )
                return existing_customer, False

            # Create new customer in Razorpay
            razorpay_customer = self.razorpay_client.create_customer(
                name=customer_data.name,
                email=customer_data.email,
                contact=customer_data.contact,
                fail_existing=customer_data.fail_existing,
                gstin=customer_data.gstin,
                notes=customer_data.notes or {}
            )

            # Store customer in our database
            db_customer = RazorpayCustomer(
                user_id=user.id,
                razorpay_customer_id=razorpay_customer["id"],
                name=customer_data.name,
                email=customer_data.email,
                contact=customer_data.contact,
                gstin=customer_data.gstin,
                notes=customer_data.notes
            )

            db.add(db_customer)
            await db.commit()
            await db.refresh(db_customer)

            logger.info(
                f"Customer created for user {user.id}",
                extra={
                    "event_type": "customer_created_in_db",
                    "user_id": user.id,
                    "customer_id": db_customer.id,
                    "razorpay_customer_id": razorpay_customer["id"]
                }
            )

            return db_customer, True

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create customer: {str(e)}")
            raise

    async def get_customer_by_user(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Optional[RazorpayCustomer]:
        """Get customer by user ID"""
        stmt = select(RazorpayCustomer).where(
            and_(RazorpayCustomer.user_id == user_id, RazorpayCustomer.is_active == True)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # === MANDATE MANAGEMENT ===

    async def create_mandate(
        self,
        db: AsyncSession,
        user: User,
        mandate_data: MandateCreate
    ) -> MandateResponse:
        """
        Create an eMandate for recurring payments
        """
        try:
            # Get or create customer
            customer_create = CustomerCreate(
                name=user.full_name or user.username,
                email=user.email,
                contact="9999999999"  # You might want to add phone to User model
            )
            customer, _ = await self.create_or_get_customer(db, user, customer_create)

            # Create order for eMandate
            order = self.razorpay_client.create_emandate_order(
                amount=mandate_data.amount,
                currency=mandate_data.currency,
                customer_id=customer.razorpay_customer_id,
                max_amount=mandate_data.max_amount,
                notes={
                    "description": mandate_data.description or "eMandate Registration",
                    "frequency": mandate_data.frequency,
                    "user_id": str(user.id)
                }
            )

            # Store mandate in database
            db_mandate = Mandate(
                customer_id=customer.id,
                razorpay_payment_id="",  # Will be updated when payment is created
                razorpay_order_id=order["id"],
                amount=mandate_data.amount,
                currency=mandate_data.currency,
                max_amount=mandate_data.max_amount,
                description=mandate_data.description,
                frequency=mandate_data.frequency,
                status=MandateStatus.CREATED,
                start_date=mandate_data.start_date,
                end_date=mandate_data.end_date,
                notes=mandate_data.notes
            )

            # Add bank account details if provided
            if mandate_data.bank_account:
                db_mandate.bank_account_number = mandate_data.bank_account.account_number
                db_mandate.bank_ifsc = mandate_data.bank_account.ifsc
                db_mandate.bank_name = mandate_data.bank_account.name

            db.add(db_mandate)
            await db.commit()
            await db.refresh(db_mandate)

            # Load customer relationship
            await db.refresh(db_mandate, ["customer"])

            logger.info(
                f"Mandate created for user {user.id}",
                extra={
                    "event_type": "mandate_created",
                    "user_id": user.id,
                    "mandate_id": db_mandate.id,
                    "order_id": order["id"],
                    "amount": mandate_data.amount
                }
            )

            return MandateResponse.from_orm(db_mandate)

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create mandate: {str(e)}")
            raise

    async def get_mandate_by_id(
        self,
        db: AsyncSession,
        mandate_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Mandate]:
        """Get mandate by ID, optionally filtered by user"""
        stmt = select(Mandate).options(selectinload(Mandate.customer))
        
        if user_id:
            stmt = stmt.join(RazorpayCustomer).where(
                and_(
                    Mandate.id == mandate_id,
                    RazorpayCustomer.user_id == user_id
                )
            )
        else:
            stmt = stmt.where(Mandate.id == mandate_id)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_mandate_status(
        self,
        db: AsyncSession,
        mandate_id: int,
        status: MandateStatus,
        token_id: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> Optional[Mandate]:
        """Update mandate status"""
        mandate = await self.get_mandate_by_id(db, mandate_id)
        if not mandate:
            return None

        mandate.status = status
        if token_id:
            mandate.token_id = token_id
        if failure_reason:
            mandate.failure_reason = failure_reason
        
        mandate.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(mandate)

        logger.info(
            f"Mandate status updated: {mandate_id} -> {status}",
            extra={
                "event_type": "mandate_status_updated",
                "mandate_id": mandate_id,
                "status": status.value,
                "token_id": token_id
            }
        )

        return mandate

    async def get_user_mandates(
        self,
        db: AsyncSession,
        user_id: int,
        status: Optional[MandateStatus] = None,
        skip: int = 0,
        limit: int = 10
    ) -> List[Mandate]:
        """Get mandates for a user"""
        stmt = select(Mandate).join(RazorpayCustomer).where(
            RazorpayCustomer.user_id == user_id
        ).options(selectinload(Mandate.customer))

        if status:
            stmt = stmt.where(Mandate.status == status)

        stmt = stmt.order_by(desc(Mandate.created_at)).offset(skip).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    # === PAYMENT OPERATIONS ===

    async def create_recurring_payment(
        self,
        db: AsyncSession,
        user: User,
        payment_data: RecurringPaymentCreate
    ) -> PaymentResponse:
        """
        Create a recurring payment using an existing mandate
        """
        try:
            # Get mandate
            mandate = await self.get_mandate_by_id(db, payment_data.mandate_id, user.id)
            if not mandate:
                raise ValidationException("Mandate not found")

            if mandate.status != MandateStatus.ACTIVE:
                raise ValidationException("Mandate is not active")

            if not mandate.token_id:
                raise ValidationException("Mandate token not available")

            # Create recurring payment
            razorpay_payment = self.razorpay_client.create_recurring_payment(
                amount=payment_data.amount,
                currency="INR",
                token_id=mandate.token_id,
                customer_id=mandate.customer.razorpay_customer_id,
                description=payment_data.description,
                receipt=payment_data.receipt,
                notes=payment_data.notes or {}
            )

            # Store payment in database
            db_payment = PaymentTransaction(
                customer_id=mandate.customer_id,
                mandate_id=mandate.id,
                razorpay_payment_id=razorpay_payment["id"],
                razorpay_order_id=razorpay_payment.get("order_id"),
                amount=payment_data.amount,
                currency="INR",
                method="emandate",
                status=PaymentStatus.CREATED,
                description=payment_data.description,
                receipt=payment_data.receipt,
                notes=payment_data.notes
            )

            # Copy payment details from Razorpay response
            if razorpay_payment.get("fee"):
                db_payment.fee = razorpay_payment["fee"]
            if razorpay_payment.get("tax"):
                db_payment.tax = razorpay_payment["tax"]

            db.add(db_payment)
            await db.commit()
            await db.refresh(db_payment)

            # Load relationships
            await db.refresh(db_payment, ["customer", "mandate"])

            logger.info(
                f"Recurring payment created for user {user.id}",
                extra={
                    "event_type": "recurring_payment_created",
                    "user_id": user.id,
                    "payment_id": db_payment.id,
                    "mandate_id": mandate.id,
                    "amount": payment_data.amount
                }
            )

            return PaymentResponse.from_orm(db_payment)

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create recurring payment: {str(e)}")
            raise

    async def get_payment_by_id(
        self,
        db: AsyncSession,
        payment_id: int,
        user_id: Optional[int] = None
    ) -> Optional[PaymentTransaction]:
        """Get payment by ID"""
        stmt = select(PaymentTransaction).options(
            selectinload(PaymentTransaction.customer),
            selectinload(PaymentTransaction.mandate)
        )

        if user_id:
            stmt = stmt.join(RazorpayCustomer).where(
                and_(
                    PaymentTransaction.id == payment_id,
                    RazorpayCustomer.user_id == user_id
                )
            )
        else:
            stmt = stmt.where(PaymentTransaction.id == payment_id)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_payments(
        self,
        db: AsyncSession,
        user_id: int,
        status: Optional[PaymentStatus] = None,
        skip: int = 0,
        limit: int = 10
    ) -> List[PaymentTransaction]:
        """Get payments for a user"""
        stmt = select(PaymentTransaction).join(RazorpayCustomer).where(
            RazorpayCustomer.user_id == user_id
        ).options(
            selectinload(PaymentTransaction.customer),
            selectinload(PaymentTransaction.mandate)
        )

        if status:
            stmt = stmt.where(PaymentTransaction.status == status)

        stmt = stmt.order_by(desc(PaymentTransaction.created_at)).offset(skip).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    # === WEBHOOK HANDLING ===

    async def process_webhook_event(
        self,
        db: AsyncSession,
        event_data: Dict,
        signature: str,
        raw_payload: str
    ) -> bool:
        """
        Process Razorpay webhook event
        """
        try:
            # Verify signature
            if not self.razorpay_client.verify_webhook_signature(raw_payload, signature):
                logger.warning("Invalid webhook signature")
                return False

            event_id = event_data.get("id")
            event_type = event_data.get("event")
            entity = event_data.get("payload", {}).get("payment", {}).get("entity", {})

            # Check if event already processed
            stmt = select(WebhookEvent).where(WebhookEvent.razorpay_event_id == event_id)
            result = await db.execute(stmt)
            existing_event = result.scalar_one_or_none()

            if existing_event:
                logger.info(f"Webhook event already processed: {event_id}")
                return True

            # Store webhook event
            webhook_event = WebhookEvent(
                razorpay_event_id=event_id,
                event_type=event_type,
                entity_id=entity.get("id", ""),
                entity_type="payment",
                payload=raw_payload,
                signature=signature,
                status=WebhookEventStatus.PENDING,
                event_created_at=datetime.fromtimestamp(event_data.get("created_at", 0))
            )

            db.add(webhook_event)
            await db.flush()

            # Process the event
            success = await self._process_payment_webhook(db, event_type, entity)

            if success:
                webhook_event.status = WebhookEventStatus.PROCESSED
                webhook_event.processed_at = datetime.utcnow()
            else:
                webhook_event.status = WebhookEventStatus.FAILED
                webhook_event.processing_error = "Failed to process webhook"

            webhook_event.processing_attempts += 1
            await db.commit()

            return success

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to process webhook: {str(e)}")
            return False

    async def _process_payment_webhook(
        self,
        db: AsyncSession,
        event_type: str,
        entity: Dict
    ) -> bool:
        """Process payment-related webhook events"""
        try:
            payment_id = entity.get("id")
            if not payment_id:
                return False

            # Find payment in our database
            stmt = select(PaymentTransaction).where(
                PaymentTransaction.razorpay_payment_id == payment_id
            )
            result = await db.execute(stmt)
            payment = result.scalar_one_or_none()

            if not payment:
                logger.warning(f"Payment not found in database: {payment_id}")
                return False

            # Update payment based on event type
            if event_type == "payment.captured":
                payment.status = PaymentStatus.CAPTURED
                payment.captured_amount = entity.get("amount", 0)
                payment.captured_at = datetime.utcnow()
                
                # Update associated mandate status if this was a mandate registration
                if payment.mandate_id and entity.get("token"):
                    await self.update_mandate_status(
                        db, payment.mandate_id, 
                        MandateStatus.ACTIVE, 
                        entity["token"]
                    )

            elif event_type == "payment.failed":
                payment.status = PaymentStatus.FAILED
                payment.error_code = entity.get("error_code")
                payment.error_description = entity.get("error_description")
                payment.error_source = entity.get("error_source")
                payment.error_step = entity.get("error_step")
                payment.error_reason = entity.get("error_reason")

                # Update mandate status if this was a mandate registration
                if payment.mandate_id:
                    await self.update_mandate_status(
                        db, payment.mandate_id,
                        MandateStatus.CANCELLED,
                        failure_reason=entity.get("error_description")
                    )

            elif event_type == "payment.authorized":
                payment.status = PaymentStatus.AUTHORIZED
                payment.authorized_at = datetime.utcnow()

            # Update other payment fields
            if entity.get("fee"):
                payment.fee = entity["fee"]
            if entity.get("tax"):
                payment.tax = entity["tax"]
            if entity.get("bank"):
                payment.bank = entity["bank"]

            payment.updated_at = datetime.utcnow()

            logger.info(
                f"Payment updated via webhook: {payment_id} -> {payment.status}",
                extra={
                    "event_type": "payment_webhook_processed",
                    "payment_id": payment_id,
                    "status": payment.status.value,
                    "webhook_event": event_type
                }
            )

            return True

        except Exception as e:
            logger.error(f"Failed to process payment webhook: {str(e)}")
            return False

    # === ANALYTICS AND REPORTING ===

    async def get_payment_statistics(
        self,
        db: AsyncSession,
        user_id: Optional[int] = None
    ) -> Dict:
        """Get payment statistics"""
        base_query = select(PaymentTransaction)
        
        if user_id:
            base_query = base_query.join(RazorpayCustomer).where(
                RazorpayCustomer.user_id == user_id
            )

        # Total payments
        total_payments_stmt = select(func.count(PaymentTransaction.id)).select_from(base_query.subquery())
        total_payments_result = await db.execute(total_payments_stmt)
        total_payments = total_payments_result.scalar()

        # Total amount
        total_amount_stmt = select(func.sum(PaymentTransaction.amount)).select_from(base_query.subquery())
        total_amount_result = await db.execute(total_amount_stmt)
        total_amount = total_amount_result.scalar() or 0

        # Successful payments
        successful_stmt = select(func.count(PaymentTransaction.id)).select_from(
            base_query.where(PaymentTransaction.status == PaymentStatus.CAPTURED).subquery()
        )
        successful_result = await db.execute(successful_stmt)
        successful_payments = successful_result.scalar()

        # Failed payments
        failed_stmt = select(func.count(PaymentTransaction.id)).select_from(
            base_query.where(PaymentTransaction.status == PaymentStatus.FAILED).subquery()
        )
        failed_result = await db.execute(failed_stmt)
        failed_payments = failed_result.scalar()

        # Active mandates
        mandate_query = select(func.count(Mandate.id))
        if user_id:
            mandate_query = mandate_query.join(RazorpayCustomer).where(
                and_(
                    RazorpayCustomer.user_id == user_id,
                    Mandate.status == MandateStatus.ACTIVE
                )
            )
        else:
            mandate_query = mandate_query.where(Mandate.status == MandateStatus.ACTIVE)

        mandate_result = await db.execute(mandate_query)
        active_mandates = mandate_result.scalar()

        return {
            "total_payments": total_payments,
            "total_amount": total_amount,
            "successful_payments": successful_payments,
            "failed_payments": failed_payments,
            "pending_payments": total_payments - successful_payments - failed_payments,
            "total_refunds": 0,  # TODO: Implement refund statistics
            "active_mandates": active_mandates,
            "total_customers": 0  # TODO: Implement customer count
        }


# Singleton instance
_payment_service: Optional[PaymentService] = None


def get_payment_service() -> PaymentService:
    """Get singleton PaymentService instance"""
    global _payment_service
    
    if _payment_service is None:
        _payment_service = PaymentService()
    
    return _payment_service 