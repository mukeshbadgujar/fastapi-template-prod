from fastapi import FastAPI

from app.middleware.logging import LoggingMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware


def setup_middlewares(app: FastAPI) -> None:
    """
    Register all middleware with the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    # Add middlewares in desired order (executed in reverse order!)
    # Last added = first executed
    
    # Add logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Setup request logger middleware and route handler
    app.add_middleware(RequestLoggerMiddleware)
