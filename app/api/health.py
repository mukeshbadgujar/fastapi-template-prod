# import time

from fastapi import APIRouter, Request, status

from app.common.response import ResponseUtil

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint for monitoring and load balancers
    """

    # Return standardized response
    return ResponseUtil.success_response(
        # data=health_data,
        message="Health check successful",
        status_code=status.HTTP_200_OK,
    )
