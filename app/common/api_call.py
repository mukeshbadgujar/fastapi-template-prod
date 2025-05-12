import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import httpx
from botocore.exceptions import ClientError
from circuitbreaker import CircuitBreaker, circuit
from fastapi import status
from httpx import AsyncClient, RequestError, Response, Timeout
from pydantic import BaseModel, SecretStr

from app.common.exceptions import ExternalAPIException, ServiceUnavailableException
from app.common.models import ApiStatus, ApiCallLog
from app.config.settings import settings
from app.utils.logger import logger
from app.common.db_logging.factory import DBLoggerFactory


# Circuit breaker configuration
class CircuitConfig:
    """
    Circuit breaker configuration
    """
    # Number of failed executions before opening the circuit
    FAILURE_THRESHOLD: int = 5
    
    # Number of successful executions before closing the circuit
    SUCCESS_THRESHOLD: int = 2
    
    # Time to wait before transitioning from open to half-open
    TIMEOUT_SECONDS: int = 30
    
    # List of exceptions that don't count as failures
    EXCLUDED_EXCEPTIONS: List[Exception] = []


# API client configuration
@dataclass
class ApiClientConfig:
    """
    API client configuration
    
    This class stores all the configurations needed for an API client.
    """
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
    api_key_header: Optional[str] = None
    
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


class ApiClient:
    """
    Reusable HTTP client for making API calls with circuit breaker pattern,
    logging, and fallback mechanism.
    """
    def __init__(self, config: ApiClientConfig):
        """
        Initialize API client with configuration
        
        Args:
            config: API client configuration
        """
        self.config = config
        self._client = None
        self._logger_factory = DBLoggerFactory()
        
        # Setup circuit breaker
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_config.FAILURE_THRESHOLD,
            recovery_timeout=config.circuit_config.TIMEOUT_SECONDS,
            expected_exception=RequestError,
            name=f"circuit-{config.vendor}"
        )
    
    async def _log_api_call(self, log_data: ApiCallLog):
        """Log API call using available loggers"""
        await self._logger_factory.log_api_call(log_data)
    
    async def close(self):
        """Close all clients and connections"""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        await self._logger_factory.close()
    
    async def _get_client(self) -> AsyncClient:
        """
        Get or create HTTP client
        
        Returns:
            AsyncClient: HTTPX async client
        """
        if self._client is None:
            auth = None
            
            # Setup basic auth if credentials are provided
            if self.config.auth_username and self.config.auth_password:
                username = self.config.auth_username
                password = self.config.auth_password
                
                # Handle SecretStr
                if isinstance(username, SecretStr):
                    username = username.get_secret_value()
                if isinstance(password, SecretStr):
                    password = password.get_secret_value()
                    
                auth = (username, password)
            
            # Setup client with config
            self._client = AsyncClient(
                base_url=self.config.base_url,
                headers=self.config.headers.copy(),
                timeout=Timeout(timeout=self.config.timeout),
                follow_redirects=self.config.follow_redirects,
                cert=self.config.cert,
                verify=self.config.verify,
                auth=auth
            )
            
        return self._client
    
    @circuit(expected_exception=RequestError)
    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        request_id: Optional[str] = None,
        partner_journey_id: Optional[str] = None,
        account_id: Optional[str] = None,
        application_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, str], int]:
        """
        Make HTTP request with circuit breaker pattern and logging
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: URL endpoint (will be appended to base_url)
            data: Form data for request
            json_data: JSON data for request
            params: Query parameters
            headers: Headers for request
            request_id: Request ID for logging
            partner_journey_id: Partner journey ID for logging
            account_id: Account ID for logging
            application_id: Application ID for logging
            
        Returns:
            Tuple of (response_data, response_headers, status_code)
            
        Raises:
            ExternalAPIException: On API error
            ServiceUnavailableException: On circuit open
        """
        # Generate request ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Get HTTP client
        client = await self._get_client()
        
        # Merge headers
        merged_headers = self.config.headers.copy()
        if headers:
            merged_headers.update(headers)
            
        # Add API key if configured
        if self.config.api_key:
            api_key = self.config.api_key
            if isinstance(api_key, SecretStr):
                api_key = api_key.get_secret_value()
                
            if self.config.api_key_header:
                merged_headers[self.config.api_key_header] = api_key
            elif self.config.api_key_query:
                if not params:
                    params = {}
                params[self.config.api_key_query] = api_key
        
        # Merge query parameters
        merged_params = self.config.default_params.copy()
        if params:
            merged_params.update(params)
            
        # URL with base_url and endpoint
        url = endpoint
        
        # Start timing
        start_time = time.time()
        
        # Log request
        log_data = ApiCallLog(
            request_id=request_id,
            endpoint=url,
            method=method.upper(),
            partner_journey_id=partner_journey_id,
            account_id=account_id,
            application_id=application_id,
            request_body=json_data if json_data else data,
            request_headers={k: "***" if k.lower() in ["authorization", "x-api-key", "apikey"] else v
                             for k, v in merged_headers.items()},
            status=ApiStatus.FAILURE,
            execution_time_ms=0,
            vendor=self.config.vendor
        )
        
        try:
            # Handle circuit open
            if self._circuit_breaker.state == 'open':
                raise ServiceUnavailableException(
                    detail=f"Circuit open for {self.config.vendor} API"
                )
                
            # Make request with proper method
            response = await client.request(
                method=method.upper(),
                url=url,
                data=data,
                json=json_data,
                params=merged_params,
                headers=merged_headers
            )
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Try to parse JSON response
            try:
                response_data = response.json()
            except Exception:
                # If not JSON, use text as response
                response_data = {"response_text": response.text}
            
            # Get response headers
            response_headers = dict(response.headers)
            
            # Update log data
            log_data.status_code = response.status_code
            log_data.response_headers = response_headers
            log_data.response_body = response_data
            log_data.execution_time_ms = round(execution_time * 1000, 2)
            
            # Check if successful response
            if 200 <= response.status_code < 300:
                log_data.status = ApiStatus.SUCCESS
                
                # Log API call
                await self._log_api_call(log_data)
                
                # Return response data, headers, and status code
                return response_data, response_headers, response.status_code
            else:
                # Error response
                error_message = f"API error: {response.status_code} - {response.text}"
                log_data.error_message = error_message
                
                # Log API call
                await self._log_api_call(log_data)
                
                # Raise exception
                raise ExternalAPIException(
                    detail=error_message,
                    service_name=self.config.vendor,
                    status_code=response.status_code,
                    response_data=response_data
                )
                
        except (RequestError, asyncio.TimeoutError, ServiceUnavailableException) as e:
            # Request error (network issue, timeout, etc.)
            execution_time = time.time() - start_time
            error_message = f"API request failed: {str(e)}"
            
            # Update log data
            log_data.error_message = error_message
            log_data.execution_time_ms = round(execution_time * 1000, 2)
            
            # Log API call
            await self._log_api_call(log_data)
            
            # Try fallback if configured
            if self.config.fallback_config:
                logger.warning(
                    f"Using fallback for {self.config.vendor} API call to {endpoint}",
                    extra={"error": str(e)}
                )
                
                # Create fallback client
                fallback_client = ApiClient(self.config.fallback_config)
                
                try:
                    # Make fallback request
                    response_data, response_headers, status_code = await fallback_client.request(
                        method=method,
                        endpoint=endpoint,
                        data=data,
                        json_data=json_data,
                        params=params,
                        headers=headers,
                        request_id=request_id,
                        partner_journey_id=partner_journey_id,
                        account_id=account_id,
                        application_id=application_id
                    )
                    
                    # Update log with fallback info
                    fallback_log = ApiCallLog(
                        request_id=request_id,
                        endpoint=url,
                        method=method.upper(),
                        partner_journey_id=partner_journey_id,
                        account_id=account_id,
                        application_id=application_id,
                        request_body=json_data if json_data else data,
                        request_headers={k: "***" if k.lower() in ["authorization", "x-api-key", "apikey"] else v
                                        for k, v in merged_headers.items()},
                        status=ApiStatus.SUCCESS,
                        execution_time_ms=log_data.execution_time_ms,
                        vendor=f"{self.config.vendor}_fallback",
                        fallback_used=True,
                        response_body=response_data,
                        response_headers=response_headers,
                        status_code=status_code
                    )
                    
                    # Log fallback API call
                    await self._log_api_call(fallback_log)
                    
                    # Close fallback client
                    await fallback_client.close()
                    
                    # Return fallback response
                    return response_data, response_headers, status_code
                    
                except Exception as fallback_error:
                    # Close fallback client
                    await fallback_client.close()
                    
                    # Re-raise original error
                    raise ServiceUnavailableException(
                        detail=f"API and fallback request failed: {str(e)} / Fallback error: {str(fallback_error)}"
                    )
            
            # No fallback or fallback failed
            raise ServiceUnavailableException(
                detail=f"API request failed: {str(e)}"
            )
            
        except Exception as e:
            # Other exceptions
            execution_time = time.time() - start_time
            error_message = f"API exception: {str(e)}"
            
            # Update log data
            log_data.error_message = error_message
            log_data.execution_time_ms = round(execution_time * 1000, 2)
            
            # Log API call
            await self._log_api_call(log_data)
            
            # Raise exception
            raise ExternalAPIException(
                detail=error_message,
                service_name=self.config.vendor
            )


# Helper functions to create API clients
def create_api_client(
    base_url: str,
    vendor: str = "unknown",
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    api_key: Optional[str] = None,
    api_key_header: Optional[str] = None,
    cert: Optional[Union[str, Tuple[str, str]]] = None,
    verify: bool = True,
    auth_username: Optional[str] = None,
    auth_password: Optional[str] = None,
    fallback_config: Optional[ApiClientConfig] = None
) -> ApiClient:
    """
    Create an API client with configuration
    
    Args:
        base_url: Base URL for the API
        vendor: Vendor name for logging
        headers: Headers for all requests
        timeout: Timeout for all requests
        api_key: API key for authentication
        api_key_header: Header name for API key
        cert: Certificate path or content
        verify: Verify SSL
        auth_username: Username for basic auth
        auth_password: Password for basic auth
        fallback_config: Fallback configuration for circuit breaker
        
    Returns:
        ApiClient: Configured API client
    """
    config = ApiClientConfig(
        base_url=base_url,
        headers=headers or {},
        timeout=timeout,
        vendor=vendor,
        cert=cert,
        verify=verify,
        api_key=api_key,
        api_key_header=api_key_header,
        auth_username=auth_username,
        auth_password=auth_password,
        fallback_config=fallback_config
    )
    
    return ApiClient(config)


def create_fallback_config(
    base_url: str,
    vendor: str = "fallback",
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    api_key: Optional[str] = None,
    api_key_header: Optional[str] = None,
    cert: Optional[Union[str, Tuple[str, str]]] = None,
    verify: bool = True,
    auth_username: Optional[str] = None,
    auth_password: Optional[str] = None
) -> ApiClientConfig:
    """
    Create a fallback configuration for an API client
    
    Args:
        base_url: Base URL for the fallback API
        vendor: Vendor name for logging
        headers: Headers for all requests
        timeout: Timeout for all requests
        api_key: API key for authentication
        api_key_header: Header name for API key
        cert: Certificate path or content
        verify: Verify SSL
        auth_username: Username for basic auth
        auth_password: Password for basic auth
        
    Returns:
        ApiClientConfig: Fallback configuration
    """
    return ApiClientConfig(
        base_url=base_url,
        headers=headers or {},
        timeout=timeout,
        vendor=vendor,
        cert=cert,
        verify=verify,
        api_key=api_key,
        api_key_header=api_key_header,
        auth_username=auth_username,
        auth_password=auth_password
    )


# Simplified API call function for easier use
async def call_api(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    api_key: Optional[str] = None,
    api_key_header: Optional[str] = None,
    vendor: str = "external-api",
    request_id: Optional[str] = None,
    account_id: Optional[str] = None,
    application_id: Optional[str] = None,
    fallback_url: Optional[str] = None,
    fallback_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Simplified function to make API calls with standardized logging and error handling
    
    This function creates a temporary API client, makes the request, and returns the response
    data in a standardized format. All the internal details like circuit breaking, logging,
    etc. are handled automatically.
    
    Args:
        url: Full URL for the API call
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        data: Form data for request (for form submissions)
        json_data: JSON data for request (for JSON APIs)
        params: Query parameters
        headers: Headers for request
        timeout: Request timeout in seconds
        api_key: API key for authentication
        api_key_header: Header name for API key (e.g., "X-API-Key")
        vendor: Vendor name for logging
        request_id: Request ID for tracing and logging
        account_id: Account ID for logging
        application_id: Application ID for logging
        fallback_url: Optional fallback URL if primary fails
        fallback_api_key: Optional fallback API key
    
    Returns:
        Dict containing:
        - success: Boolean indicating if the call was successful
        - data: Response data if successful
        - status_code: HTTP status code
        - error: Error details if not successful
        - execution_time_ms: Request execution time in milliseconds
        - fallback_used: Whether fallback was used
    
    Example:
        result = await call_api(
            url="https://api.example.com/users",
            method="POST",
            json_data={"name": "John Doe"},
            api_key="your-api-key",
            api_key_header="X-API-Key"
        )

        if result["success"]:
            user_data = result["data"]
            print(f"User created with ID: {user_data['id']}")
        else:
            print(f"Error: {result['error']}")
    """
    # Extract domain from URL for base URL
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    endpoint = parsed_url.path
    if parsed_url.query:
        endpoint = f"{endpoint}?{parsed_url.query}"
    
    # Setup fallback if provided
    fallback_config = None
    if fallback_url:
        parsed_fallback = urlparse(fallback_url)
        fallback_base_url = f"{parsed_fallback.scheme}://{parsed_fallback.netloc}"
        
        fallback_config = create_fallback_config(
            base_url=fallback_base_url,
            vendor=f"{vendor}-fallback",
            api_key=fallback_api_key,
            api_key_header=api_key_header if api_key_header else "X-API-Key",
            timeout=timeout
        )
    
    # Create API client
    client = create_api_client(
        base_url=base_url,
        vendor=vendor,
        headers=headers,
        timeout=timeout,
        api_key=api_key,
        api_key_header=api_key_header,
        fallback_config=fallback_config
    )
    
    try:
        # Make the request
        start_time = time.time()
        response_data, response_headers, status_code = await client.request(
            method=method,
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            params=params,
            headers=headers,
            request_id=request_id,
            account_id=account_id,
            application_id=application_id
        )
        execution_time = time.time() - start_time
        
        # Return standardized successful response
        return {
            "success": True,
            "data": response_data,
            "status_code": status_code,
            "headers": response_headers,
            "execution_time_ms": round(execution_time * 1000, 2),
            "fallback_used": False
        }
        
    except ExternalAPIException as e:
        # Handle API error
        return {
            "success": False,
            "error": str(e.detail),
            "status_code": e.status_code,
            "error_data": getattr(e, "response_data", None),
            "execution_time_ms": 0,
            "fallback_used": False
        }
        
    except ServiceUnavailableException as e:
        # Handle service unavailable
        return {
            "success": False,
            "error": str(e.detail),
            "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
            "execution_time_ms": 0,
            "fallback_used": "fallback" in str(e.detail).lower()
        }
        
    except Exception as e:
        # Handle unexpected errors
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "execution_time_ms": 0,
            "fallback_used": False
        }
        
    finally:
        # Always close the client
        try:
            await client.close()
        except:
            pass 