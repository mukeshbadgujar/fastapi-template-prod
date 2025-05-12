import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """
    Test the health check endpoint
    """
    response = await client.get("/api/health")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ok",
        "message": "Service is up and running"
    }
