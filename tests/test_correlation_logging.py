"""
Tests for enhanced correlation logging functionality
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.common.api_call import create_correlation_client, with_correlation_context
from app.core.logging_backend import get_db_logger, log_api_request, log_internal_api_call
from app.utils.logger import generate_correlation_id, get_correlation_id, logger, set_correlation_id


class TestCorrelationLogging:
    """Test correlation ID generation and propagation"""

    def test_correlation_id_generation(self):
        """Test that correlation IDs are properly generated"""
        correlation_id = generate_correlation_id()
        assert correlation_id is not None
        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 36  # UUID4 format

    def test_correlation_id_context(self):
        """Test correlation ID context setting and retrieval"""
        test_id = str(uuid.uuid4())

        # Initially no correlation ID
        assert get_correlation_id() is None

        # Set correlation ID
        set_correlation_id(test_id)

        # Verify it can be retrieved
        assert get_correlation_id() == test_id

    def test_logger_context_setting(self):
        """Test logger context setting functionality"""
        # Test setting various context fields
        logger.set_context(
            correlation_id="test-correlation-123",
            account_id="account-456",
            partner_journey_id="journey-789"
        )

        # Note: In actual implementation, we would verify these are included in log output
        # This is a basic test to ensure the method doesn't raise errors
        logger.info("Test log message")

        # Clear context
        logger.clear_context()

    @pytest.mark.asyncio
    async def test_correlation_decorator(self):
        """Test the correlation context decorator"""

        # Set a correlation ID
        test_correlation_id = str(uuid.uuid4())
        set_correlation_id(test_correlation_id)

        @with_correlation_context
        async def test_service_call(data: dict, correlation_id: str = None):
            # Verify correlation ID is automatically injected
            assert correlation_id == test_correlation_id
            return {"processed": True}

        result = await test_service_call({"test": "data"})
        assert result["processed"] is True

    @pytest.mark.asyncio
    async def test_correlation_http_client_creation(self):
        """Test creation of correlation-aware HTTP client"""
        client = create_correlation_client(
            base_url="https://api.example.com",
            vendor="test-service",
            api_key="test-key"
        )

        assert client.base_url == "https://api.example.com"
        assert client.vendor == "test-service"
        assert client.api_key == "test-key"
        assert client.propagate_correlation is True

        await client.close()

    @pytest.mark.asyncio
    async def test_database_logging_functions(self):
        """Test database logging convenience functions"""

        # Mock database logger to avoid actual DB operations in tests
        with patch('app.core.logging_backend.get_db_logger') as mock_get_logger:
            mock_logger = AsyncMock()
            mock_logger.log_api_request.return_value = True
            mock_logger.log_internal_api_call.return_value = True
            mock_get_logger.return_value = mock_logger

            # Test API request logging
            success = await log_api_request(
                correlation_id="test-123",
                method="GET",
                path="/test",
                status_code=200
            )
            assert success is True

            # Test internal API call logging
            success = await log_internal_api_call(
                correlation_id="test-123",
                vendor="test-service",
                method="POST",
                url="https://api.example.com/test",
                status_code=201
            )
            assert success is True


@pytest.mark.asyncio
async def test_end_to_end_correlation_flow():
    """
    Test end-to-end correlation flow simulation
    """
    # Generate correlation ID (simulating middleware)
    correlation_id = generate_correlation_id()
    set_correlation_id(correlation_id)

    # Log incoming request (simulating request logger middleware)
    logger.info("Incoming request", extra={
        "event_type": "request_start",
        "method": "POST",
        "path": "/api/users"
    })

    # Simulate service processing
    @with_correlation_context
    async def user_service_call(user_data: dict, correlation_id: str = None):
        logger.info("Processing user data", extra={
            "event_type": "service_processing",
            "user_id": user_data.get("id")
        })

        # Simulate external API call
        # In real implementation, this would use CorrelationHTTPClient
        logger.info("Making external API call", extra={
            "event_type": "external_api_call",
            "vendor": "user-service",
            "endpoint": "/validate"
        })

        return {"status": "processed", "correlation_id": correlation_id}

    # Execute the flow
    result = await user_service_call({"id": "user123", "name": "Test User"})

    # Verify correlation ID was propagated
    assert result["correlation_id"] == correlation_id

    # Log completion (simulating request logger middleware)
    logger.info("Request completed", extra={
        "event_type": "request_complete",
        "status_code": 201,
        "execution_time_ms": 150.5
    })


if __name__ == "__main__":
    # Run basic tests without pytest
    test_instance = TestCorrelationLogging()

    print("Testing correlation ID generation...")
    test_instance.test_correlation_id_generation()
    print("✓ Correlation ID generation test passed")

    print("Testing correlation ID context...")
    test_instance.test_correlation_id_context()
    print("✓ Correlation ID context test passed")

    print("Testing logger context setting...")
    test_instance.test_logger_context_setting()
    print("✓ Logger context setting test passed")

    print("All basic tests passed! Run with pytest for async tests.")
