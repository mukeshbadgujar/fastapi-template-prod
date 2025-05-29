#!/usr/bin/env python3
"""
Demonstration script for enhanced logging features
Run this to see the correlation tracking and logging capabilities in action
"""
import asyncio
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.common.api_call import create_correlation_client, with_correlation_context
from app.config.settings import settings
from app.utils.logger import generate_correlation_id, logger, set_correlation_id


async def demo_correlation_tracking():
    """Demonstrate correlation ID tracking throughout request chain"""

    print("🚀 Enhanced FastAPI Logging Demo")
    print("=" * 50)

    # 1. Generate correlation ID (simulating incoming request)
    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)

    print(f"📝 Generated correlation ID: {correlation_id}")

    # 2. Log incoming request
    logger.info("Incoming API request", extra={
        "event_type": "request_start",
        "method": "POST",
        "path": "/api/users",
        "client_ip": "192.168.1.100"
    })

    # 3. Set additional context
    logger.set_context(
        account_id="account_123",
        partner_journey_id="journey_456"
    )

    # 4. Process with correlation context
    @with_correlation_context
    async def process_user_data(user_data: dict, correlation_id: str = None):
        logger.info("Processing user data", extra={
            "event_type": "service_processing",
            "user_id": user_data.get("id"),
            "action": "create_user"
        })

        # Simulate some processing time
        await asyncio.sleep(0.1)

        return {"status": "processed", "user_id": user_data.get("id")}

    # 5. Execute processing
    result = await process_user_data({"id": "user_123", "name": "John Doe"})

    # 6. Simulate external API call (with circuit breaker protection)
    try:
        # This would normally make a real HTTP request
        logger.info("Making external API call", extra={
            "event_type": "external_api_request_start",
            "vendor": "user-validation-service",
            "method": "POST",
            "endpoint": "/validate"
        })

        # Simulate API response
        await asyncio.sleep(0.05)

        logger.info("External API call completed", extra={
            "event_type": "external_api_request_complete",
            "vendor": "user-validation-service",
            "status_code": 200,
            "execution_time_ms": 50.0
        })

    except Exception as e:
        logger.error("External API call failed", extra={
            "event_type": "external_api_request_error",
            "vendor": "user-validation-service",
            "error_type": type(e).__name__,
            "error_message": str(e)
        })

    # 7. Log request completion
    logger.info("Request completed successfully", extra={
        "event_type": "request_complete",
        "status_code": 201,
        "execution_time_ms": 155.5,
        "response_size": 256
    })

    print("\n✅ Correlation tracking demonstration completed!")
    print(f"🔗 All logs above should contain correlation_id: {correlation_id}")


def demo_logging_configuration():
    """Demonstrate various logging configuration options"""

    print("\n📊 Logging Configuration Demo")
    print("=" * 50)

    print(f"🎛️  Current logging configuration:")
    print(f"   LOG_FORMAT: {settings.LOG_FORMAT}")
    print(f"   LOG_LEVEL: {settings.LOG_LEVEL}")
    print(f"   LOG_COLOR: {settings.LOG_COLOR}")
    print(f"   LOG_PRETTY: {settings.LOG_PRETTY}")
    print(f"   ENABLE_CORRELATION_ID: {settings.ENABLE_CORRELATION_ID}")
    print(f"   CORRELATION_ID_HEADER: {settings.CORRELATION_ID_HEADER}")

    print(f"\n📁 Database logging configuration:")
    print(f"   LOG_DB_URL: {settings.LOG_DB_URL}")
    print(f"   API_LOG_TABLE: {settings.API_LOG_TABLE}")
    print(f"   INT_API_LOG_TABLE: {settings.INT_API_LOG_TABLE}")

    # Demonstrate different log levels with colors
    print(f"\n🎨 Log level demonstration (with colors if enabled):")
    logger.debug("This is a DEBUG message - development details")
    logger.info("This is an INFO message - general information")
    logger.warning("This is a WARNING message - something to watch")
    logger.error("This is an ERROR message - something went wrong")
    logger.critical("This is a CRITICAL message - urgent attention needed")


def demo_structured_logging():
    """Demonstrate structured logging capabilities"""

    print("\n📋 Structured Logging Demo")
    print("=" * 50)

    # Business event logging
    logger.info("User registration started", extra={
        "event_type": "user_registration_start",
        "user_email": "john.doe@example.com",
        "registration_source": "web_app",
        "referral_code": "FRIEND123"
    })

    # Performance monitoring
    logger.info("Database query executed", extra={
        "event_type": "database_query",
        "query_type": "SELECT",
        "table": "users",
        "execution_time_ms": 45.2,
        "rows_returned": 1
    })

    # Security event
    logger.warning("Multiple login attempts detected", extra={
        "event_type": "security_alert",
        "user_id": "user_123",
        "client_ip": "192.168.1.100",
        "attempt_count": 5,
        "alert_level": "medium"
    })

    # Business metrics
    logger.info("Transaction completed", extra={
        "event_type": "transaction_complete",
        "transaction_id": "txn_789",
        "amount": 250.00,
        "currency": "USD",
        "payment_method": "credit_card"
    })


async def demo_error_tracking():
    """Demonstrate error tracking with correlation"""

    print("\n🐛 Error Tracking Demo")
    print("=" * 50)

    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)

    try:
        # Simulate an error condition
        await process_payment({"amount": -100, "currency": "INVALID"})
    except ValueError as e:
        logger.error("Payment processing failed", extra={
            "event_type": "payment_error",
            "error_type": "validation_error",
            "error_details": {
                "field": "amount",
                "value": -100,
                "reason": "negative_amount_not_allowed"
            }
        })

    try:
        # Simulate another error with exception tracking
        raise ConnectionError("External payment service unavailable")
    except ConnectionError as e:
        logger.exception("External service error occurred", extra={
            "event_type": "external_service_error",
            "service": "payment_gateway",
            "retry_count": 3
        })


async def process_payment(payment_data: dict):
    """Simulate payment processing that can fail"""
    if payment_data.get("amount", 0) < 0:
        raise ValueError("Payment amount cannot be negative")

    if payment_data.get("currency") not in ["USD", "EUR", "GBP"]:
        raise ValueError("Invalid currency code")


async def main():
    """Run all demonstrations"""

    print("🎯 FastAPI Production Template - Enhanced Logging Demonstration")
    print("=" * 70)

    # Show current configuration
    demo_logging_configuration()

    # Demonstrate correlation tracking
    await demo_correlation_tracking()

    # Show structured logging
    demo_structured_logging()

    # Show error tracking
    await demo_error_tracking()

    print("\n" + "=" * 70)
    print("🎉 Demonstration completed!")
    print("💡 Check your logs to see the correlation IDs and structured data")
    print("📊 If LOG_DB_URL is configured, check your database for logged requests")
    print("🔧 Modify env_example.txt and copy to .env to customize logging behavior")


if __name__ == "__main__":
    asyncio.run(main())
