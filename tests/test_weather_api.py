import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_weather():
    """Test the weather endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/weather?city=London")
        
        # If API key is not set, we expect a failure response
        assert response.status_code == 200
        
        data = response.json()
        
        # Check response structure is correct even if API call failed
        assert "status" in data
        assert "timestamp" in data
        
        # Note: actual weather data validation requires valid API key
        if data["status"] == "success":
            assert "data" in data
            weather_data = data["data"]
            assert "city_name" in weather_data
            assert "temperature" in weather_data
            assert "description" in weather_data 