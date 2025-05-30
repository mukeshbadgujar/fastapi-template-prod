"""
Razorpay Client for eMandate Integration
Uses official Razorpay Python SDK with existing logging and error handling
"""

import base64
import hashlib
import hmac
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import razorpay
from razorpay.errors import BadRequestError, ServerError

from app.common.exceptions import ExternalAPIException
from app.config.settings import settings
from app.utils.logger import logger


class RazorpayClient:
    """
    Razorpay client using official Python SDK
    Handles eMandate operations with proper logging and error handling
    """

    def __init__(self):
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        self.environment = settings.RAZORPAY_ENVIRONMENT

        # Validate configuration
        if not self.key_id or not self.key_secret:
            raise ValueError("Razorpay credentials not configured")

        # Initialize official Razorpay client
        self.client = razorpay.Client(auth=(self.key_id, self.key_secret))

        logger.info(
            f"Razorpay client initialized for {self.environment} environment",
            extra={
                "event_type": "razorpay_client_initialized",
                "environment": self.environment,
                "vendor": "razorpay"
            }
        )

    def _handle_razorpay_error(self, operation: str, error: Exception) -> None:
        """Handle and log Razorpay SDK errors"""
        error_msg = f"Razorpay {operation} failed: {str(error)}"
        
        logger.error(
            error_msg,
            extra={
                "event_type": "razorpay_operation_error",
                "operation": operation,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )
        
        # Re-raise as our custom exception
        raise ExternalAPIException(error_msg)

    # === CUSTOMER MANAGEMENT ===

    def create_customer(
        self,
        name: str,
        email: str,
        contact: str,
        fail_existing: bool = False,
        **additional_fields
    ) -> Dict[str, Any]:
        """
        Create a new customer in Razorpay
        
        Args:
            name: Customer name
            email: Customer email
            contact: Customer phone number
            fail_existing: Whether to fail if customer already exists
            **additional_fields: Additional customer fields
        
        Returns:
            Dict containing customer data
        """
        customer_data = {
            "name": name,
            "email": email,
            "contact": contact,
            "fail_existing": fail_existing,
            **additional_fields
        }

        try:
            logger.info(
                f"Creating Razorpay customer: {email}",
                extra={
                    "event_type": "customer_creation_start",
                    "email": email,
                    "vendor": "razorpay"
                }
            )

            response = self.client.customer.create(customer_data)
            
            logger.info(
                f"Customer created successfully: {response.get('id')}",
                extra={
                    "event_type": "customer_created",
                    "customer_id": response.get("id"),
                    "email": email,
                    "vendor": "razorpay"
                }
            )
            
            return response

        except BadRequestError as e:
            # Handle case where customer already exists
            if "customer_already_exists" in str(e):
                logger.warning(f"Customer already exists: {email}")
                # Try to fetch existing customer
                return self.get_customer_by_email(email)
            
            self._handle_razorpay_error("create_customer", e)
        except Exception as e:
            self._handle_razorpay_error("create_customer", e)

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer details by ID"""
        try:
            logger.info(
                f"Fetching customer: {customer_id}",
                extra={
                    "event_type": "customer_fetch_start",
                    "customer_id": customer_id,
                    "vendor": "razorpay"
                }
            )

            response = self.client.customer.fetch(customer_id)
            return response

        except Exception as e:
            self._handle_razorpay_error("get_customer", e)

    def get_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find customer by email address"""
        try:
            logger.info(
                f"Searching customer by email: {email}",
                extra={
                    "event_type": "customer_search_start",
                    "email": email,
                    "vendor": "razorpay"
                }
            )

            customers = self.client.customer.all({"email": email})
            
            if customers.get("items"):
                return customers["items"][0]
            return None

        except Exception as e:
            logger.error(f"Failed to search customer by email: {str(e)}")
            return None

    # === ORDER MANAGEMENT ===

    def create_order(
        self,
        amount: int,
        currency: str = "INR",
        receipt: Optional[str] = None,
        customer_id: Optional[str] = None,
        **order_options
    ) -> Dict[str, Any]:
        """
        Create an order in Razorpay
        
        Args:
            amount: Amount in smallest currency unit (paise for INR)
            currency: Currency code
            receipt: Receipt identifier
            customer_id: Razorpay customer ID
            **order_options: Additional order options
        
        Returns:
            Dict containing order data
        """
        order_data = {
            "amount": amount,
            "currency": currency,
            **order_options
        }

        if receipt:
            order_data["receipt"] = receipt
        if customer_id:
            order_data["customer_id"] = customer_id

        try:
            logger.info(
                f"Creating Razorpay order: amount={amount}",
                extra={
                    "event_type": "order_creation_start",
                    "amount": amount,
                    "currency": currency,
                    "customer_id": customer_id,
                    "vendor": "razorpay"
                }
            )

            response = self.client.order.create(order_data)
            
            logger.info(
                f"Order created successfully: {response.get('id')}",
                extra={
                    "event_type": "order_created",
                    "order_id": response.get("id"),
                    "amount": amount,
                    "customer_id": customer_id,
                    "vendor": "razorpay"
                }
            )
            
            return response

        except Exception as e:
            self._handle_razorpay_error("create_order", e)

    # === EMANDATE OPERATIONS ===

    def create_emandate_order(
        self,
        amount: int,
        currency: str = "INR",
        customer_id: Optional[str] = None,
        max_amount: Optional[int] = None,
        expire_by: Optional[int] = None,
        **order_options
    ) -> Dict[str, Any]:
        """
        Create an order specifically for eMandate registration
        
        Args:
            amount: Amount in smallest currency unit (paise for INR)
            currency: Currency code
            customer_id: Razorpay customer ID
            max_amount: Maximum amount for the mandate
            expire_by: Unix timestamp when order expires
            **order_options: Additional order options
        
        Returns:
            Dict containing order data
        """
        order_data = {
            "amount": amount,
            "currency": currency,
            "method": "emandate",
            **order_options
        }

        if customer_id:
            order_data["customer_id"] = customer_id
        if max_amount:
            order_data["notes"] = {"max_amount": str(max_amount)}
        if expire_by:
            order_data["expire_by"] = expire_by

        try:
            logger.info(
                f"Creating eMandate order: amount={amount}",
                extra={
                    "event_type": "emandate_order_creation_start",
                    "amount": amount,
                    "max_amount": max_amount,
                    "customer_id": customer_id,
                    "vendor": "razorpay"
                }
            )

            response = self.client.order.create(order_data)
            
            logger.info(
                f"eMandate order created: {response.get('id')}",
                extra={
                    "event_type": "emandate_order_created",
                    "order_id": response.get("id"),
                    "amount": amount,
                    "customer_id": customer_id,
                    "vendor": "razorpay"
                }
            )
            
            return response

        except Exception as e:
            self._handle_razorpay_error("create_emandate_order", e)

    # === PAYMENT OPERATIONS ===

    def create_payment(
        self,
        amount: int,
        currency: str = "INR",
        order_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        method: str = "emandate",
        **payment_options
    ) -> Dict[str, Any]:
        """
        Create a payment
        
        Args:
            amount: Amount in smallest currency unit
            currency: Currency code
            order_id: Order ID
            customer_id: Customer ID
            method: Payment method
            **payment_options: Additional payment options
        
        Returns:
            Dict containing payment data
        """
        payment_data = {
            "amount": amount,
            "currency": currency,
            "method": method,
            **payment_options
        }

        if order_id:
            payment_data["order_id"] = order_id
        if customer_id:
            payment_data["customer_id"] = customer_id

        try:
            logger.info(
                f"Creating payment: amount={amount}, method={method}",
                extra={
                    "event_type": "payment_creation_start",
                    "amount": amount,
                    "method": method,
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "vendor": "razorpay"
                }
            )

            response = self.client.payment.create(payment_data)
            
            logger.info(
                f"Payment created: {response.get('id')}",
                extra={
                    "event_type": "payment_created",
                    "payment_id": response.get("id"),
                    "amount": amount,
                    "method": method,
                    "vendor": "razorpay"
                }
            )
            
            return response

        except Exception as e:
            self._handle_razorpay_error("create_payment", e)

    def create_recurring_payment(
        self,
        amount: int,
        currency: str = "INR",
        token_id: str = None,
        customer_id: str = None,
        **payment_options
    ) -> Dict[str, Any]:
        """
        Create a recurring payment using existing token
        
        Args:
            amount: Amount in smallest currency unit
            currency: Currency code
            token_id: Token ID from successful mandate
            customer_id: Customer ID
            **payment_options: Additional payment options
        
        Returns:
            Dict containing payment data
        """
        payment_data = {
            "amount": amount,
            "currency": currency,
            "recurring": "1",  # Indicates recurring payment
            **payment_options
        }

        if customer_id:
            payment_data["customer_id"] = customer_id
        if token_id:
            payment_data["token"] = token_id

        try:
            logger.info(
                f"Creating recurring payment: amount={amount}, token={token_id}",
                extra={
                    "event_type": "recurring_payment_creation_start",
                    "amount": amount,
                    "token_id": token_id,
                    "customer_id": customer_id,
                    "vendor": "razorpay"
                }
            )

            response = self.client.payment.create(payment_data)
            
            logger.info(
                f"Recurring payment created: {response.get('id')}",
                extra={
                    "event_type": "recurring_payment_created",
                    "payment_id": response.get("id"),
                    "amount": amount,
                    "token_id": token_id,
                    "vendor": "razorpay"
                }
            )
            
            return response

        except Exception as e:
            self._handle_razorpay_error("create_recurring_payment", e)

    def capture_payment(self, payment_id: str, amount: int) -> Dict[str, Any]:
        """Capture a payment"""
        try:
            logger.info(
                f"Capturing payment: {payment_id}, amount={amount}",
                extra={
                    "event_type": "payment_capture_start",
                    "payment_id": payment_id,
                    "amount": amount,
                    "vendor": "razorpay"
                }
            )

            response = self.client.payment.capture(payment_id, amount)
            
            logger.info(
                f"Payment captured: {payment_id}",
                extra={
                    "event_type": "payment_captured",
                    "payment_id": payment_id,
                    "amount": amount,
                    "vendor": "razorpay"
                }
            )
            
            return response

        except Exception as e:
            self._handle_razorpay_error("capture_payment", e)

    def get_payment_details(self, payment_id: str) -> Dict[str, Any]:
        """Get detailed payment information"""
        try:
            logger.info(
                f"Fetching payment details: {payment_id}",
                extra={
                    "event_type": "payment_fetch_start",
                    "payment_id": payment_id,
                    "vendor": "razorpay"
                }
            )

            response = self.client.payment.fetch(payment_id)
            return response

        except Exception as e:
            self._handle_razorpay_error("get_payment_details", e)

    # === TOKEN OPERATIONS (for eMandate) ===

    def get_tokens_by_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get all tokens for a customer"""
        try:
            logger.info(
                f"Fetching tokens for customer: {customer_id}",
                extra={
                    "event_type": "tokens_fetch_start",
                    "customer_id": customer_id,
                    "vendor": "razorpay"
                }
            )

            response = self.client.token.all({"customer_id": customer_id})
            return response.get("items", [])

        except Exception as e:
            logger.error(f"Failed to fetch tokens: {str(e)}")
            return []

    def get_token_details(self, token_id: str) -> Dict[str, Any]:
        """Get token details"""
        try:
            response = self.client.token.fetch(token_id)
            return response

        except Exception as e:
            self._handle_razorpay_error("get_token_details", e)

    # === WEBHOOK OPERATIONS ===

    def verify_webhook_signature(
        self,
        payload: str,
        signature: str,
        secret: Optional[str] = None
    ) -> bool:
        """
        Verify Razorpay webhook signature using SDK utility
        
        Args:
            payload: Raw webhook payload
            signature: Signature from X-Razorpay-Signature header
            secret: Webhook secret (uses configured secret if not provided)
        
        Returns:
            True if signature is valid
        """
        if not secret:
            secret = self.webhook_secret

        if not secret:
            logger.error("Webhook secret not configured")
            return False

        try:
            # Use Razorpay SDK's utility for verification
            is_valid = razorpay.utility.verify_webhook_signature(
                payload, signature, secret
            )
            
            logger.info(
                f"Webhook signature verification: {'valid' if is_valid else 'invalid'}",
                extra={
                    "event_type": "webhook_signature_verification",
                    "is_valid": is_valid,
                    "vendor": "razorpay"
                }
            )
            
            return is_valid

        except Exception as e:
            logger.error(
                f"Webhook signature verification failed: {str(e)}",
                extra={
                    "event_type": "webhook_signature_error",
                    "error": str(e),
                    "vendor": "razorpay"
                }
            )
            return False

    # === UTILITY METHODS ===

    def list_payments(
        self,
        from_timestamp: Optional[int] = None,
        to_timestamp: Optional[int] = None,
        count: int = 10,
        skip: int = 0
    ) -> Dict[str, Any]:
        """List payments with optional filters"""
        params = {
            "count": count,
            "skip": skip
        }

        if from_timestamp:
            params["from"] = from_timestamp
        if to_timestamp:
            params["to"] = to_timestamp

        try:
            response = self.client.payment.all(params)
            return response

        except Exception as e:
            self._handle_razorpay_error("list_payments", e)

    def create_refund(
        self,
        payment_id: str,
        amount: Optional[int] = None,
        speed: str = "normal",
        receipt: Optional[str] = None,
        notes: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a refund"""
        refund_data = {
            "speed": speed
        }

        if amount:
            refund_data["amount"] = amount
        if receipt:
            refund_data["receipt"] = receipt
        if notes:
            refund_data["notes"] = notes

        try:
            logger.info(
                f"Creating refund for payment: {payment_id}",
                extra={
                    "event_type": "refund_creation_start",
                    "payment_id": payment_id,
                    "amount": amount,
                    "vendor": "razorpay"
                }
            )

            response = self.client.payment.refund(payment_id, refund_data)
            
            logger.info(
                f"Refund created: {response.get('id')}",
                extra={
                    "event_type": "refund_created",
                    "refund_id": response.get("id"),
                    "payment_id": payment_id,
                    "amount": amount,
                    "vendor": "razorpay"
                }
            )
            
            return response

        except Exception as e:
            self._handle_razorpay_error("create_refund", e)


# Singleton instance
_razorpay_client: Optional[RazorpayClient] = None


def get_razorpay_client() -> RazorpayClient:
    """Get singleton Razorpay client instance"""
    global _razorpay_client
    
    if _razorpay_client is None:
        _razorpay_client = RazorpayClient()
    
    return _razorpay_client 