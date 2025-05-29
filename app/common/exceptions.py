from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """
    Base exception class for all API exceptions

    All API exceptions should inherit from this class to ensure consistent
    error handling and response format.
    """
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred"
    headers: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        detail: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize with custom detail message and headers
        """
        actual_detail = detail if detail is not None else self.detail
        actual_headers = headers if headers is not None else self.headers

        super().__init__(
            status_code=self.status_code,
            detail=actual_detail,
            headers=actual_headers
        )


class NotFoundException(BaseAPIException):
    """Exception raised when resource is not found"""
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found"


class UnauthorizedException(BaseAPIException):
    """Exception raised for authentication errors"""
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication failed"
    headers = {"WWW-Authenticate": "Bearer"}


class ForbiddenException(BaseAPIException):
    """Exception raised for permission errors"""
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Insufficient permissions"


class ValidationException(BaseAPIException):
    """Exception for validation errors in request data"""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error"


class BadRequestException(BaseAPIException):
    """Exception for general bad request errors"""
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Bad request"


class ConflictException(BaseAPIException):
    """Exception for resource conflicts"""
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource conflict"


class InternalServerErrorException(BaseAPIException):
    """Exception for unexpected server errors"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Internal server error"


class ServiceUnavailableException(BaseAPIException):
    """Exception for unavailable external services"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Service unavailable"


class TooManyRequestsException(BaseAPIException):
    """Exception for rate limiting"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    detail = "Too many requests"


class ExternalAPIException(BaseAPIException):
    """Exception for external API call failures"""
    status_code = status.HTTP_502_BAD_GATEWAY
    detail = "External API call failed"

    def __init__(
        self,
        detail: Optional[str] = None,
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize with external API call details

        Args:
            detail: Error message
            service_name: Name of the external service
            status_code: HTTP status code from external service
            response_data: Response data from external service
            headers: Additional response headers
        """
        if status_code is not None:
            self.status_code = status_code

        # Create detailed error message
        message = detail if detail else self.detail
        if service_name:
            message = f"{message} - Service: {service_name}"

        # Include response data as extra
        self.response_data = response_data

        super().__init__(
            detail=message,
            headers=headers
        )
