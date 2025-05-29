import time

from fastapi import APIRouter, Request

from app.common.response import ResponseUtil
from app.config.settings import settings

router = APIRouter(tags=["Home"])


@router.get("/")
async def home(request: Request):
    """
    Home endpoint returning API information
    """

    # Create API info data
    api_info = {
        "name": settings.PROJECT_NAME,
        "description": settings.PROJECT_DESCRIPTION,
        "version": settings.VERSION,
        "environment": settings.ENV.upper(),
        "docs_urls": {
            "swagger": f"{settings.API_PREFIX}/docs",
            "redoc": f"{settings.API_PREFIX}/redoc"
        }
    }

    # Return standardized response
    return ResponseUtil.success_response(
        data=api_info,
        message="Welcome to the API",
    )
