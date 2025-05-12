from datetime import datetime
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.common.exception_handlers import register_exception_handlers
from app.common.response import CustomJSONResponse
from app.config.settings import settings
from app.middleware.base import setup_middlewares
from app.routes import register_routes


# Custom JSON encoder for FastAPI responses
class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Override FastAPI's default JSONResponse encoder
class CustomJSONResponse(JSONResponse):
    """Custom JSONResponse that uses our CustomJSONEncoder"""
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CustomJSONEncoder,
        ).encode("utf-8")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application
    """
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        default_response_class=CustomJSONResponse,  # Use our custom JSONResponse
    )

    # Setup CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup custom middlewares
    setup_middlewares(application)
    
    # Register exception handlers
    register_exception_handlers(application)

    # Register all API routes using the centralized function
    register_routes(application)

    return application


app = create_application()


@app.on_event("startup")
async def startup_event():
    """Application startup: register core events"""
    # You can initialize db, redis, etc. here
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown: de-register core events"""
    # You can close db connections, etc. here
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
