import time
from typing import Any, Dict, List, Union

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.common.exceptions import BaseAPIException
from app.common.response import ErrorDetail, ErrorCode, ResponseUtil, CustomJSONResponse
from app.utils.logger import logger


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    # Register handlers for different exception types
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(BaseAPIException, api_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


async def http_exception_handler(request: Request, exc: HTTPException) -> CustomJSONResponse:
    """
    Handle standard HTTPExceptions and return formatted response
    
    Args:
        request: FastAPI request
        exc: HTTPException
        
    Returns:
        Standardized error response
    """
    request_id = getattr(request.state, "request_id", None)
    start_time = getattr(request.state, "start_time", None)
    
    # Calculate processing time if start_time exists
    elapsed_ms = None
    if start_time:
        elapsed_ms = (time.time() - start_time) * 1000
    
    # Log the exception
    logger.error(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # Convert to standard error response
    error = ErrorDetail(
        code=get_error_code_for_status(exc.status_code),
        message=str(exc.detail)
    )
    
    return ResponseUtil.error_response(
        errors=[error],
        message=str(exc.detail),
        status_code=exc.status_code,
        request_id=request_id,
        elapsed_ms=elapsed_ms
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> CustomJSONResponse:
    """
    Handle validation errors and return formatted response
    
    Args:
        request: FastAPI request
        exc: RequestValidationError
        
    Returns:
        Standardized error response
    """
    request_id = getattr(request.state, "request_id", None)
    start_time = getattr(request.state, "start_time", None)
    
    # Calculate processing time if start_time exists
    elapsed_ms = None
    if start_time:
        elapsed_ms = (time.time() - start_time) * 1000
    
    # Convert validation errors to a list of dicts
    errors = exc.errors()
    
    # Log the validation errors
    logger.error(
        f"Validation error: {len(errors)} validation errors",
        extra={
            "validation_errors": errors,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return ResponseUtil.validation_error(
        errors=errors,
        message="Request validation error",
        request_id=request_id,
        elapsed_ms=elapsed_ms
    )


async def api_exception_handler(request: Request, exc: BaseAPIException) -> CustomJSONResponse:
    """
    Handle custom API exceptions and return formatted response
    
    Args:
        request: FastAPI request
        exc: BaseAPIException
        
    Returns:
        Standardized error response
    """
    request_id = getattr(request.state, "request_id", None)
    start_time = getattr(request.state, "start_time", None)
    
    # Calculate processing time if start_time exists
    elapsed_ms = None
    if start_time:
        elapsed_ms = (time.time() - start_time) * 1000
    
    # Log the exception
    logger.error(
        f"API exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # Convert to standard error response
    error = ErrorDetail(
        code=get_error_code_for_status(exc.status_code),
        message=str(exc.detail)
    )
    
    return ResponseUtil.error_response(
        errors=[error],
        message=str(exc.detail),
        status_code=exc.status_code,
        request_id=request_id,
        elapsed_ms=elapsed_ms
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> CustomJSONResponse:
    """
    Handle unhandled exceptions and return formatted response
    
    Args:
        request: FastAPI request
        exc: Unhandled exception
        
    Returns:
        Standardized error response
    """
    request_id = getattr(request.state, "request_id", None)
    start_time = getattr(request.state, "start_time", None)
    
    # Calculate processing time if start_time exists
    elapsed_ms = None
    if start_time:
        elapsed_ms = (time.time() - start_time) * 1000
    
    # Log the exception
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # Use a generic error message for security reasons
    return ResponseUtil.server_error(
        message="An unexpected error occurred",
        request_id=request_id,
        elapsed_ms=elapsed_ms
    )


def get_error_code_for_status(status_code: int) -> str:
    """
    Map HTTP status code to an error code
    
    Args:
        status_code: HTTP status code
        
    Returns:
        Error code string
    """
    error_code_map = {
        400: ErrorCode.BAD_REQUEST,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        409: ErrorCode.CONFLICT,
        422: ErrorCode.UNPROCESSABLE_ENTITY,
        429: ErrorCode.TOO_MANY_REQUESTS,
        500: ErrorCode.INTERNAL_SERVER_ERROR,
        502: ErrorCode.EXTERNAL_SERVICE_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
        504: ErrorCode.GATEWAY_TIMEOUT,
    }
    
    return error_code_map.get(status_code, ErrorCode.INTERNAL_SERVER_ERROR) 