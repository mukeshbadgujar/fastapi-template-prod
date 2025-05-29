from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from app.common.api_call import call_api
from app.common.response import ResponseUtil
from app.config.settings import settings
from app.schemas.weather import WeatherData, WeatherRequest

router = APIRouter(tags=["Weather"])

@router.get("/weather")
async def get_weather(
    city: str = Query(..., description="City name", example="London"),
    country_code: Optional[str] = Query(None, description="Country code (ISO 3166)", example="uk"),
    units: str = Query("metric", description="Units of measurement", example="metric")
):
    """
    Get current weather information for a specified city.

    Uses OpenWeatherMap API to fetch current weather data.
    """
    # Form the location query parameter
    location = city
    if country_code:
        location = f"{city},{country_code}"

    # Make the API call using our utility
    api_result = await call_api(
        url=f"https://api.openweathermap.org/data/2.5/weather",
        method="GET",
        params={
            "q": location,
            "units": units,
            "appid": settings.OPENWEATHERMAP_API_KEY
        },
        vendor="openweathermap",
        timeout=10.0
    )

    # Handle API response
    if not api_result["success"]:
        return ResponseUtil.error_response(
            errors=[{
                "code": "EXTERNAL_API_ERROR",
                "message": f"Failed to fetch weather data: {api_result['error']}"
            }],
            message=f"Failed to fetch weather data",
            status_code=api_result["status_code"] or status.HTTP_503_SERVICE_UNAVAILABLE,
            elapsed_ms=api_result.get("execution_time_ms")
        )

    # Extract and transform the weather data
    weather_data = api_result["data"]
    result = WeatherData(
        city_name=weather_data["name"],
        temperature=weather_data["main"]["temp"],
        feels_like=weather_data["main"]["feels_like"],
        humidity=weather_data["main"]["humidity"],
        description=weather_data["weather"][0]["description"],
        wind_speed=weather_data["wind"]["speed"]
    )

    return ResponseUtil.success_response(
        data=result.model_dump(),
        message="Weather data retrieved successfully",
        elapsed_ms=api_result["execution_time_ms"]
    )

@router.post("/weather")
async def create_weather_request(request: WeatherRequest):
    """
    Get current weather information using POST request with JSON body.

    Uses the same OpenWeatherMap API but with a more structured request format.
    """
    # Form the location query parameter
    location = request.city
    if request.country_code:
        location = f"{request.city},{request.country_code}"

    # Make the API call using our utility
    api_result = await call_api(
        url=f"https://api.openweathermap.org/data/2.5/weather",
        method="GET",  # OpenWeatherMap still uses GET, we're just accepting a POST body
        params={
            "q": location,
            "units": request.units,
            "appid": settings.OPENWEATHERMAP_API_KEY
        },
        vendor="openweathermap",
        timeout=10.0
    )

    # Handle API response
    if not api_result["success"]:
        return ResponseUtil.error_response(
            errors=[{
                "code": "EXTERNAL_API_ERROR",
                "message": f"Failed to fetch weather data: {api_result['error']}"
            }],
            message=f"Failed to fetch weather data",
            status_code=api_result["status_code"] or status.HTTP_503_SERVICE_UNAVAILABLE,
            elapsed_ms=api_result.get("execution_time_ms")
        )

    # Extract and transform the weather data
    weather_data = api_result["data"]
    result = WeatherData(
        city_name=weather_data["name"],
        temperature=weather_data["main"]["temp"],
        feels_like=weather_data["main"]["feels_like"],
        humidity=weather_data["main"]["humidity"],
        description=weather_data["weather"][0]["description"],
        wind_speed=weather_data["wind"]["speed"]
    )

    return ResponseUtil.success_response(
        data=result.model_dump(),
        message="Weather data retrieved successfully",
        elapsed_ms=api_result["execution_time_ms"]
    )
