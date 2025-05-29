from typing import Optional

from pydantic import BaseModel, Field


class WeatherRequest(BaseModel):
    """Weather request model with strict validation"""
    city: str = Field(..., description="City name", example="London")
    country_code: Optional[str] = Field(None, description="Country code (ISO 3166)", example="uk")
    units: str = Field("metric", description="Units of measurement", example="metric")

    # Prevent extra fields
    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "city": "London",
                    "country_code": "uk",
                    "units": "metric"
                }
            ]
        }
    }


class WeatherData(BaseModel):
    """Weather response data model"""
    city_name: str = Field(..., description="City name")
    temperature: float = Field(..., description="Current temperature")
    feels_like: float = Field(..., description="Feels like temperature")
    humidity: int = Field(..., description="Humidity percentage")
    description: str = Field(..., description="Weather description")
    wind_speed: float = Field(..., description="Wind speed")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "city_name": "London",
                    "temperature": 15.2,
                    "feels_like": 14.8,
                    "humidity": 76,
                    "description": "scattered clouds",
                    "wind_speed": 4.1
                }
            ]
        }
    }
