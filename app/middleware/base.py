from fastapi import FastAPI

from app.middleware.logging import LoggingMiddleware
from app.middleware.request_logger import setup_logging_middlewares


def setup_middlewares(app: FastAPI) -> None:
    """
    Register all middleware with the FastAPI application

    Args:
        app: FastAPI application instance
    """
    # Add middlewares in desired order (executed in reverse order!)
    # Last added = first executed

    # Add basic logging middleware
    app.add_middleware(LoggingMiddleware)

    # Setup enhanced request logging with correlation tracking
    setup_logging_middlewares(app)
