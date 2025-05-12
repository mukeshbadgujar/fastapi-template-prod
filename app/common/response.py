from datetime import datetime
from enum import Enum
import json
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# Type for the data payload
T = TypeVar("T")


class ResponseStatus(str, Enum):
    """API response status values"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class ErrorDetail(BaseModel):
    """Model for error details"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field with error (for validation errors)")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")


class CustomJSONResponse(JSONResponse):
    """Custom JSONResponse that properly handles datetime objects"""
    def render(self, content) -> bytes:
        return json.dumps(
            content, 
            ensure_ascii=False, 
            separators=(",", ":"), 
            default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o)
        ).encode("utf-8")


# Standard error codes
class ErrorCode:
    """Standard error codes for API responses"""
    # General errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    UNPROCESSABLE_ENTITY = "UNPROCESSABLE_ENTITY"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Authentication errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    
    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    
    # External service errors
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"


class ResponseUtil:
    """Utility class for generating standardized API responses"""
    
    @staticmethod
    def success_response(
        data: Any = None, 
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK,
        request_id: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
        pagination: Optional[Dict[str, Any]] = None,
    ) -> CustomJSONResponse:
        """
        Generate a successful API response
        
        Args:
            data: Response payload
            message: Optional success message
            status_code: HTTP status code
            request_id: Request ID for tracing
            elapsed_ms: Time taken to process the request in milliseconds
            pagination: Optional pagination information
            
        Returns:
            JSONResponse object with standardized format
        """
        response_id = f"res_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        # Build response content
        response_content = {
            "status": "success",
            "timestamp": datetime.utcnow(),
            "status_code": status_code
        }
        
        # Add data if provided
        if data is not None:
            response_content["data"] = data
            
        # Add message if provided
        if message:
            response_content["message"] = message
            
        # Add pagination if provided
        if pagination:
            response_content["pagination"] = pagination
        
        # Create custom response
        response = CustomJSONResponse(
            content=response_content,
            status_code=status_code,
            media_type="application/json"
        )
        
        # Add headers for tracing and monitoring
        if request_id:
            response.headers["X-Request-ID"] = request_id
        
        response.headers["X-Response-ID"] = response_id
        
        if elapsed_ms:
            response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
        
        return response

    @staticmethod
    def error_response(
        errors: Union[Dict[str, Any], List[Dict[str, Any]]],
        message: Optional[str] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        request_id: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
    ) -> CustomJSONResponse:
        """
        Generate an error API response
        
        Args:
            errors: Error details or list of error details
            message: Optional error message
            status_code: HTTP status code
            request_id: Request ID for tracing
            elapsed_ms: Time taken to process the request in milliseconds
            
        Returns:
            JSONResponse object with standardized format
        """
        response_id = f"res_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        # Convert single error to list
        if not isinstance(errors, list):
            errors = [errors]
        
        # Build response content
        response_content = {
            "status": "error",
            "timestamp": datetime.utcnow(),
            "status_code": status_code,
            "errors": errors
        }
        
        # Add message if provided
        if message:
            response_content["message"] = message
        
        # Create custom response
        response = CustomJSONResponse(
            content=response_content,
            status_code=status_code,
            media_type="application/json"
        )
        
        # Add headers for tracing and monitoring
        if request_id:
            response.headers["X-Request-ID"] = request_id
        
        response.headers["X-Response-ID"] = response_id
        
        if elapsed_ms:
            response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
        
        return response

    @staticmethod
    def warning_response(
        data: Any = None,
        message: str = "Warning",
        status_code: int = status.HTTP_200_OK,
        request_id: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
        errors: Optional[List[Dict[str, Any]]] = None,
    ) -> CustomJSONResponse:
        """
        Generate a warning API response
        
        Args:
            data: Response payload
            message: Warning message
            status_code: HTTP status code
            request_id: Request ID for tracing
            elapsed_ms: Time taken to process the request in milliseconds
            errors: Optional list of warning details
            
        Returns:
            JSONResponse object with standardized format
        """
        response_id = f"res_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        # Build response content
        response_content = {
            "status": "warning",
            "timestamp": datetime.utcnow(),
            "status_code": status_code
        }
        
        # Add data if provided
        if data is not None:
            response_content["data"] = data
            
        # Add message if provided
        if message:
            response_content["message"] = message
            
        # Add errors if provided
        if errors:
            response_content["errors"] = errors
        
        # Create custom response
        response = CustomJSONResponse(
            content=response_content,
            status_code=status_code,
            media_type="application/json"
        )
        
        # Add headers for tracing and monitoring
        if request_id:
            response.headers["X-Request-ID"] = request_id
        
        response.headers["X-Response-ID"] = response_id
        
        if elapsed_ms:
            response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
        
        return response
        
    # Convenience methods for common errors
    @classmethod
    def not_found(
        cls, 
        message: str = "Resource not found",
        entity: Optional[str] = None,
        request_id: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
    ) -> CustomJSONResponse:
        """Generate a not found error response"""
        detail_msg = message
        if entity:
            detail_msg = f"{entity} not found"
            
        error = {
            "code": ErrorCode.NOT_FOUND,
            "message": detail_msg
        }
        
        return cls.error_response(
            errors=[error],
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            elapsed_ms=elapsed_ms
        )
    
    @classmethod
    def validation_error(
        cls,
        errors: List[Dict[str, Any]],
        message: str = "Validation error",
        request_id: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
    ) -> CustomJSONResponse:
        """Generate a validation error response from validation errors"""
        error_details = []
        
        for error in errors:
            loc = error.get("loc", [])
            field = ".".join(str(item) for item in loc[1:]) if len(loc) > 1 else ""
            
            error_details.append({
                "code": ErrorCode.VALIDATION_ERROR,
                "message": error.get("msg", "Invalid value"),
                "field": field,
                "details": {"type": error.get("type", "")}
            })
        
        return cls.error_response(
            errors=error_details,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=request_id,
            elapsed_ms=elapsed_ms
        )
    
    @classmethod
    def server_error(
        cls,
        message: str = "Internal server error",
        request_id: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
    ) -> CustomJSONResponse:
        """Generate a server error response"""
        error = {
            "code": ErrorCode.INTERNAL_SERVER_ERROR,
            "message": message
        }
        
        return cls.error_response(
            errors=[error],
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            elapsed_ms=elapsed_ms
        )
    
    @classmethod
    def unauthorized(
        cls,
        message: str = "Authentication required",
        request_id: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
    ) -> CustomJSONResponse:
        """Generate an unauthorized error response"""
        error = {
            "code": ErrorCode.UNAUTHORIZED,
            "message": message
        }
        
        response = cls.error_response(
            errors=[error],
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            request_id=request_id,
            elapsed_ms=elapsed_ms
        )
        
        response.headers["WWW-Authenticate"] = "Bearer"
        return response
    
    @classmethod
    def forbidden(
        cls,
        message: str = "Permission denied",
        request_id: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
    ) -> CustomJSONResponse:
        """Generate a forbidden error response"""
        error = {
            "code": ErrorCode.FORBIDDEN,
            "message": message
        }
        
        return cls.error_response(
            errors=[error],
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            request_id=request_id,
            elapsed_ms=elapsed_ms
        )
    
    @classmethod
    def bad_request(
        cls,
        message: str = "Bad request",
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
    ) -> CustomJSONResponse:
        """Generate a bad request error response"""
        error = {
            "code": ErrorCode.BAD_REQUEST,
            "message": message
        }
        
        if details:
            error["details"] = details
        
        return cls.error_response(
            errors=[error],
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            request_id=request_id,
            elapsed_ms=elapsed_ms
        ) 