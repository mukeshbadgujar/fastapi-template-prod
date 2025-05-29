from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, Field, field_validator
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
    # Database URL - supports SQLite, PostgreSQL, MySQL, etc.
    DATABASE_URL: Optional[str] = None
    # Fallback to SQLite for development if no DATABASE_URL is provided
    SQLITE_URL: str = "sqlite:///./sql_app.db"

    # Docker Database Config
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "fastapi"

    # Use SQLite by default for development
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: Optional[str]) -> str:
        if v:
            return v
        return "sqlite:///./sql_app.db"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # === ENHANCED LOGGING CONFIGURATION ===

    # Pluggable Logging Backend - Single ENV var to control which DB to use
    LOG_DB_URL: str = Field(
        default="sqlite:///./api_logs.db",
        description="Database URL for logging (SQLite, PostgreSQL, MySQL, etc.)"
    )

    # Configurable table names for different log types
    API_LOG_TABLE: str = Field(
        default="api_request_logs",
        description="Table name for API request logs"
    )

    INT_API_LOG_TABLE: str = Field(
        default="internal_api_logs",
        description="Table name for internal/3rd-party API call logs"
    )

    # Legacy fields - kept for backward compatibility but deprecated
    API_LOG_MONGO_URI: Optional[str] = None
    API_LOG_DYNAMODB_TABLE: Optional[str] = None
    API_LOG_MONGO_ENABLED: bool = False
    API_LOG_DYNAMODB_ENABLED: bool = False
    API_LOG_SQLITE_ENABLED: bool = True
    API_LOG_FALLBACK_ENABLED: bool = True
    API_LOG_SQLITE_PATH: str = "api_logs.db"
    API_LOG_REAL_TIME: bool = True

    # === ADVANCED LOGGING CONFIGURATION ===

    # JSON Logging Configuration
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format: 'json' for structured logging, 'pretty' for human-readable"
    )

    LOG_PRETTY: bool = Field(
        default=False,
        description="Enable pretty/human-readable logging format"
    )

    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )

    # Console color configuration
    LOG_COLOR: bool = Field(
        default=True,
        description="Enable colored console output"
    )

    # Correlation tracking
    ENABLE_CORRELATION_ID: bool = Field(
        default=True,
        description="Enable automatic correlation ID generation and propagation"
    )

    CORRELATION_ID_HEADER: str = Field(
        default="X-Correlation-ID",
        description="Header name for correlation ID"
    )

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

    # === VALIDATION METHODS ===

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard levels"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {valid_levels}")
        return v.upper()

    @field_validator("LOG_FORMAT")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format is supported"""
        valid_formats = ["json", "pretty"]
        if v.lower() not in valid_formats:
            raise ValueError(f"LOG_FORMAT must be one of: {valid_formats}")
        return v.lower()


# Create settings instance
settings = Settings()
