from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.home import router as home_router
from app.api.template import router as template_router
from app.api.weather import router as weather_router
from app.config.settings import settings


def register_routes(app: FastAPI) -> None:
    """
    Register all API routes with the FastAPI application
    
    This function centralizes all route registration in one place,
    making it easier to manage as the number of routes grows.
    
    Args:
        app: FastAPI application instance
    """
    # Register routes in a structured manner
    
    # Base routes (no prefix)
    app.include_router(home_router)  # Root route '/'
    
    # API routes (with API prefix)
    app.include_router(health_router, prefix=settings.API_PREFIX)
    app.include_router(template_router, prefix=settings.API_PREFIX)
    app.include_router(weather_router, prefix=settings.API_PREFIX)
    
    # Add more route groups as needed, for example:
    # Auth routes
    # app.include_router(auth_router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
    
    # User routes
    # app.include_router(user_router, prefix=f"{settings.API_PREFIX}/users", tags=["Users"])
    
    # Admin routes
    # app.include_router(admin_router, prefix=f"{settings.API_PREFIX}/admin", tags=["Admin"]) 