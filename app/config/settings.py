from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, Field, PostgresDsn, validator, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable support
    """
    # Project info
    PROJECT_NAME: str = "FastAPI Template"
    PROJECT_DESCRIPTION: str = "A production-ready FastAPI template"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # Environment
    ENV: str = "dev"  # dev, uat, prod, preprod
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    # Database URL format: postgresql://user:password@host:port/database
    DATABASE_URL: Optional[PostgresDsn] = None
    # Fallback to SQLite for development if no DATABASE_URL is provided
    SQLITE_URL: str = "sqlite:///./sql_app.db"
    
    # Docker Database Config
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "fastapi"
    
    # Use SQLite by default for development
    @validator("DATABASE_URL", pre=True)
    def assemble_db_url(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if v:
            return v
        return values.get("SQLITE_URL")

    # CORS
    CORS_ORIGINS: Union[List[str], str] = []

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # API Logging
    API_LOG_MONGO_URI: Optional[str] = None
    API_LOG_DYNAMODB_TABLE: Optional[str] = None
    
    # API Logging Configuration
    API_LOG_MONGO_ENABLED: bool = False
    API_LOG_DYNAMODB_ENABLED: bool = False
    API_LOG_SQLITE_ENABLED: bool = True
    API_LOG_FALLBACK_ENABLED: bool = True
    API_LOG_SQLITE_PATH: str = "api_logs.db"
    
    # AWS Credentials already we have in env variables so no need to set it here
    # Explicitly add AWS region to avoid validation errors
    AWS_REGION: Optional[str] = None

    # Redis Settings
    REDIS_URL: Optional[str] = None
    
    # Third-party API keys
    OPENWEATHERMAP_API_KEY: str = Field("", env="OPENWEATHERMAP_API_KEY")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }


# Create settings instance
settings = Settings()
