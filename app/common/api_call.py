import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from circuitbreaker import CircuitBreaker, CircuitBreakerError, circuit
from fastapi import status
from httpx import AsyncClient, RequestError, Response, Timeout
from pydantic import BaseModel, SecretStr

from app.common.exceptions import ExternalAPIException, ServiceUnavailableException
from app.config.settings import settings
from app.models.models_request_response import ApiCallLog, ApiStatus
from app.utils.logger import get_correlation_id, logger


# Circuit breaker configuration
@dataclass
class CircuitConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 30
    excluded_exceptions: List[Exception] = field(default_factory=list)


# Unified API client configuration
@dataclass
class ApiClientConfig:
    """Unified API client configuration"""
    # Base URL for the API (required)
    base_url: str
    
    # Default headers to use for all requests
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Default timeout for all requests (in seconds)
    timeout: float = 30.0
    
    # Allow redirects
    follow_redirects: bool = True
    
    # Vendor name for logging
    vendor: str = "unknown"
    
    # Custom certificate path or content
    cert: Optional[Union[str, Tuple[str, str]]] = None
    
    # Verify SSL
    verify: bool = True
    
    # API key for authentication
    api_key: Optional[Union[str, SecretStr]] = None
    
    # API key header name
    api_key_header: Optional[str] = "X-API-Key"
    
    # API key query parameter name
    api_key_query: Optional[str] = None
    
    # Username for basic auth
    auth_username: Optional[Union[str, SecretStr]] = None
    
    # Password for basic auth
    auth_password: Optional[Union[str, SecretStr]] = None
    
    # Default query parameters
    default_params: Dict[str, str] = field(default_factory=dict)
    
    # Circuit breaker configuration
    circuit_config: CircuitConfig = field(default_factory=CircuitConfig)
    
    # Fallback configuration
    fallback_config: Optional['ApiClientConfig'] = None


class UnifiedAPIClient:
    """
    Unified HTTP client with automatic correlation ID propagation, circuit breaker, and comprehensive logging
    """

    def __init__(self, config: ApiClientConfig):
        """
        Initialize the unified API client

        Args:
            config: ApiClientConfig with all necessary settings
        """
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.vendor = config.vendor
        
        # Setup circuit breaker
        self._circuit_breaker = circuit(
            failure_threshold=config.circuit_config.failure_threshold,
            recovery_timeout=config.circuit_config.timeout_seconds,
            expected_exception=(httpx.HTTPError, httpx.TimeoutException)
        )(self._make_request)

        # Create HTTP client
        client_kwargs = {
            "timeout": httpx.Timeout(config.timeout),
            "follow_redirects": config.follow_redirects,
            "verify": config.verify,
        }
        
        if config.cert:
            client_kwargs["cert"] = config.cert
            
        self._client = httpx.AsyncClient(**client_kwargs)

    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        account_id: Optional[str] = None,
        partner_journey_id: Optional[str] = None,
        **kwargs
    ) -> Tuple[Dict[str, Any], Dict[str, str], int]:
        """
        Make an HTTP request with correlation tracking and comprehensive logging

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            headers: Additional headers
            account_id: Account ID for logging context
            partner_journey_id: Partner journey ID for logging context
            **kwargs: Additional arguments for httpx

        Returns:
            Tuple of (response_data, response_headers, status_code)
        """

        # Prepare URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Prepare headers
        request_headers = self.config.headers.copy()
        
        # Add authentication
        if self.config.api_key:
            api_key_value = self.config.api_key
            if isinstance(api_key_value, SecretStr):
                api_key_value = api_key_value.get_secret_value()
            request_headers[self.config.api_key_header] = api_key_value

        # Add correlation headers
        correlation_id = get_correlation_id()
        if correlation_id:
            request_headers[settings.CORRELATION_ID_HEADER] = correlation_id
            request_headers["X-Request-ID"] = correlation_id

        # Merge with provided headers
        if headers:
            request_headers.update(headers)

        # Merge params with defaults
        final_params = self.config.default_params.copy()
        if params:
            final_params.update(params)
            
        # Add API key to query params if configured
        if self.config.api_key_query and self.config.api_key:
            api_key_value = self.config.api_key
            if isinstance(api_key_value, SecretStr):
                api_key_value = api_key_value.get_secret_value()
            final_params[self.config.api_key_query] = api_key_value

        # Set logging context for this call
        call_context = {
            "vendor": self.vendor,
            "endpoint": endpoint,
            "method": method.upper(),
            "url": url,
        }

        if account_id:
            call_context["account_id"] = account_id
            logger.set_context(account_id=account_id)

        if partner_journey_id:
            call_context["partner_journey_id"] = partner_journey_id
            logger.set_context(partner_journey_id=partner_journey_id)

        # Start timing
        start_time = time.time()

        # Log outgoing request
        logger.info(
            f"Outgoing {method.upper()} request to {self.vendor}",
            extra={
                "event_type": "external_api_request_start",
                "vendor": self.vendor,
                "method": method.upper(),
                "url": url,
                "endpoint": endpoint,
                "request_data": self._sanitize_data(data),
                "query_params": final_params,
                "headers": self._sanitize_headers(request_headers),
            }
        )

        try:
            # Make the request with circuit breaker protection
            response_data, response_headers, status_code = await self._circuit_breaker(
                method=method,
                url=url,
                data=data,
                params=final_params,
                headers=request_headers,
                **kwargs
            )

            # Calculate execution time
            execution_time_ms = round((time.time() - start_time) * 1000, 2)

            # Log successful response
            logger.info(
                f"Received response from {self.vendor} - {status_code}",
                extra={
                    "event_type": "external_api_request_complete",
                    "vendor": self.vendor,
                    "method": method.upper(),
                    "url": url,
                    "endpoint": endpoint,
                    "status_code": status_code,
                    "execution_time_ms": execution_time_ms,
                    "response_data": self._sanitize_data(response_data),
                    "response_headers": self._sanitize_headers(response_headers),
                }
            )

            # Log to database for internal API tracking
            await self._log_to_database(
                vendor=self.vendor,
                method=method.upper(),
                url=url,
                endpoint=endpoint,
                request_data=data,
                request_params=final_params,
                request_headers=request_headers,
                response_data=response_data,
                response_headers=response_headers,
                status_code=status_code,
                execution_time_ms=execution_time_ms,
                account_id=account_id,
                partner_journey_id=partner_journey_id,
            )

            return response_data, response_headers, status_code

        except CircuitBreakerError as e:
            execution_time_ms = round((time.time() - start_time) * 1000, 2)

            logger.error(
                f"Circuit breaker open for {self.vendor}",
                extra={
                    "event_type": "external_api_circuit_breaker",
                    "vendor": self.vendor,
                    "method": method.upper(),
                    "url": url,
                    "endpoint": endpoint,
                    "execution_time_ms": execution_time_ms,
                    "error": str(e),
                }
            )
            
            # Try fallback if configured
            if self.config.fallback_config:
                logger.info(f"Attempting fallback for {self.vendor}")
                fallback_client = UnifiedAPIClient(self.config.fallback_config)
                try:
                    return await fallback_client.request(
                        method, endpoint, data, params, headers, 
                        account_id, partner_journey_id, **kwargs
                    )
                finally:
                    await fallback_client.close()
            
            raise ServiceUnavailableException(f"Service {self.vendor} is currently unavailable")

        except Exception as e:
            execution_time_ms = round((time.time() - start_time) * 1000, 2)

            logger.error(
                f"Request to {self.vendor} failed: {str(e)}",
                extra={
                    "event_type": "external_api_request_error",
                    "vendor": self.vendor,
                    "method": method.upper(),
                    "url": url,
                    "endpoint": endpoint,
                    "execution_time_ms": execution_time_ms,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            
            # Log error to database
            await self._log_to_database(
                vendor=self.vendor,
                method=method.upper(),
                url=url,
                endpoint=endpoint,
                request_data=data,
                request_params=final_params,
                request_headers=request_headers,
                response_data=None,
                response_headers={},
                status_code=getattr(e, 'status_code', None),
                execution_time_ms=execution_time_ms,
                account_id=account_id,
                partner_journey_id=partner_journey_id,
                error_message=str(e),
                error_type=type(e).__name__,
            )
            
            raise ExternalAPIException(f"External API call failed: {str(e)}")

    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Tuple[Dict[str, Any], Dict[str, str], int]:
        """Internal method to make the actual HTTP request"""

        # Prepare authentication
        auth = None
        if self.config.auth_username and self.config.auth_password:
            username = self.config.auth_username
            password = self.config.auth_password
            if isinstance(username, SecretStr):
                username = username.get_secret_value()
            if isinstance(password, SecretStr):
                password = password.get_secret_value()
            auth = (username, password)

        # Prepare request body
        json_data = None
        if data is not None:
            json_data = data

        # Make the request
        response = await self._client.request(
            method=method,
            url=url,
            json=json_data,
            params=params,
            headers=headers,
            auth=auth,
            **kwargs
        )

        # Parse response
        try:
            response_data = response.json() if response.content else {}
        except json.JSONDecodeError:
            response_data = {"raw_content": response.text}

        response_headers = dict(response.headers)

        # Raise for HTTP errors
        response.raise_for_status()

        return response_data, response_headers, response.status_code

    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize data for logging (remove sensitive information)"""

        if not data:
            return data

        if isinstance(data, dict):
            sanitized = {}
            sensitive_keys = {
                'password', 'secret', 'token', 'api_key', 'authorization',
                'credit_card', 'ssn', 'social_security', 'bank_account'
            }

            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    sanitized[key] = "***REDACTED***"
                elif isinstance(value, dict):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value

            return sanitized

        return data

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers for logging"""

        if not headers:
            return headers

        sanitized = {}
        sensitive_headers = {
            'authorization', 'x-api-key', 'api-key', 'token', 'cookie'
        }

        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value

        return sanitized

    async def _log_to_database(self, **log_data):
        """Log internal API call to database using the pluggable backend"""

        try:
            # Import here to avoid circular imports
            from app.core.logging_backend import log_internal_api_call

            # Generate unique call ID for this specific API call
            call_id = str(uuid.uuid4())

            # Get correlation ID from current context
            correlation_id = get_correlation_id()

            # Prepare log data for database storage
            db_log_data = {
                "correlation_id": correlation_id,
                "parent_request_id": correlation_id,  # Same as correlation for now
                "call_id": call_id,
                "timestamp": datetime.utcnow(),
                "vendor": log_data.get("vendor"),
                "method": log_data.get("method"),
                "url": log_data.get("url"),
                "endpoint": log_data.get("endpoint"),
                "request_data": self._sanitize_data(log_data.get("request_data")),
                "request_params": log_data.get("request_params"),
                "request_headers": self._sanitize_headers(log_data.get("request_headers", {})),
                "status_code": log_data.get("status_code"),
                "response_data": self._sanitize_data(log_data.get("response_data")),
                "response_headers": self._sanitize_headers(log_data.get("response_headers", {})),
                "execution_time_ms": log_data.get("execution_time_ms"),
                "account_id": log_data.get("account_id"),
                "partner_journey_id": log_data.get("partner_journey_id"),
                "application_id": log_data.get("application_id"),
                "error_message": None,
                "error_type": None,
                "circuit_breaker_open": False,
                "fallback_used": False,
            }

            # Log to database
            success = await log_internal_api_call(**db_log_data)

            if success:
                logger.debug(
                    "Internal API call logged to database successfully",
                    extra={
                        "event_type": "internal_api_db_log_success",
                        "table": settings.INT_API_LOG_TABLE,
                        "correlation_id": correlation_id,
                        "vendor": log_data.get("vendor"),
                        "call_id": call_id,
                    }
                )
            else:
                logger.warning(
                    "Failed to log internal API call to database",
                    extra={
                        "event_type": "internal_api_db_log_failure",
                        "table": settings.INT_API_LOG_TABLE,
                        "correlation_id": correlation_id,
                        "vendor": log_data.get("vendor"),
                    }
                )

        except Exception as e:
            logger.error(
                f"Exception while logging internal API call to database: {e}",
                extra={
                    "event_type": "internal_api_db_log_exception",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "correlation_id": get_correlation_id(),
                    "vendor": log_data.get("vendor"),
                }
            )

    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()


# Factory functions for easy client creation
def create_api_client(
    base_url: str,
    vendor: str = "unknown",
    api_key: Optional[str] = None,
    api_key_header: str = "X-API-Key",
    timeout: float = 30.0,
    **kwargs
) -> UnifiedAPIClient:
    """
    Create a unified API client

    Args:
        base_url: Base URL for the API
        vendor: Vendor/service name
        api_key: API key for authentication
        api_key_header: Header name for API key
        timeout: Request timeout in seconds
        **kwargs: Additional client options

    Returns:
        UnifiedAPIClient instance
    """
    config = ApiClientConfig(
        base_url=base_url,
        vendor=vendor,
        api_key=api_key,
        api_key_header=api_key_header,
        timeout=timeout,
        **kwargs
    )
    return UnifiedAPIClient(config)


# Legacy compatibility functions
async def call_api(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    vendor: str = "unknown",
    timeout: float = 30.0,
    account_id: Optional[str] = None,
    partner_journey_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Legacy call_api function for backward compatibility

    Returns a dict with success/error format expected by existing code:
    {
        "success": bool,
        "data": dict | None,
        "error": str | None,
        "status_code": int | None,
        "execution_time_ms": float
    }
    """

    try:
        # Parse base URL and endpoint from the full URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        endpoint = parsed.path

        # Merge query params if endpoint has them
        if parsed.query:
            if params:
                params.update(dict(pair.split('=') for pair in parsed.query.split('&') if '=' in pair))
            else:
                params = dict(pair.split('=') for pair in parsed.query.split('&') if '=' in pair)

        # Create unified client
        client = create_api_client(
            base_url=base_url,
            vendor=vendor,
            timeout=timeout
        )

        try:
            # Make the request
            response_data, response_headers, status_code = await client.request(
                method=method,
                endpoint=endpoint,
                data=data,
                params=params,
                headers=headers,
                account_id=account_id,
                partner_journey_id=partner_journey_id,
                **kwargs
            )

            return {
                "success": True,
                "data": response_data,
                "error": None,
                "status_code": status_code,
                "execution_time_ms": 0.0,  # Would need to be tracked separately
            }

        finally:
            await client.close()

    except Exception as e:
        # Return error format expected by legacy code
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "status_code": getattr(e, 'status_code', None) if hasattr(e, 'status_code') else None,
            "execution_time_ms": 0.0,
        }


# Decorator for internal service calls to attach correlation context
def with_correlation_context(func):
    """
    Decorator to automatically set correlation context for internal service calls
    """
    async def wrapper(*args, **kwargs):
        # Get current correlation ID
        correlation_id = get_correlation_id()

        if correlation_id:
            # Set context for this service call
            logger.set_context(correlation_id=correlation_id)

            # Add correlation_id to kwargs if not present
            if 'correlation_id' not in kwargs:
                kwargs['correlation_id'] = correlation_id

        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(
                f"Service call failed: {func.__name__}",
                extra={
                    "event_type": "service_call_error",
                    "function": func.__name__,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            raise

    return wrapper


# Backward compatibility aliases
ApiClient = UnifiedAPIClient
CorrelationHTTPClient = UnifiedAPIClient
create_correlation_client = create_api_client
