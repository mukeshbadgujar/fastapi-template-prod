"""
Pluggable database logging backend for API requests and internal calls
"""
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.utils.logger import logger

Base = declarative_base()


class APIRequestLog(Base):
    """
    Model for API request logs (incoming requests)
    """
    __tablename__ = settings.API_LOG_TABLE

    id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id = Column(String(255), index=True)
    request_id = Column(String(255), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Request details
    method = Column(String(10), index=True)
    path = Column(String(500), index=True)
    url = Column(Text)
    query_params = Column(JSON)
    headers = Column(JSON)
    body = Column(JSON)
    body_size = Column(Integer)

    # Response details
    status_code = Column(Integer, index=True)
    response_headers = Column(JSON)
    response_body = Column(JSON)
    response_size = Column(Integer)

    # Timing and client info
    execution_time_ms = Column(Float, index=True)
    client_ip = Column(String(45))  # IPv6 support
    user_agent = Column(Text)

    # Context
    account_id = Column(String(255), index=True)
    partner_journey_id = Column(String(255), index=True)
    application_id = Column(String(255), index=True)
    user_id = Column(String(255), index=True)

    # Error handling
    error_message = Column(Text)
    error_type = Column(String(255))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class InternalAPILog(Base):
    """
    Model for internal/3rd-party API call logs (outgoing requests)
    """
    __tablename__ = settings.INT_API_LOG_TABLE

    id = Column(Integer, primary_key=True, autoincrement=True)
    correlation_id = Column(String(255), index=True)
    parent_request_id = Column(String(255), index=True)  # Links to original request
    call_id = Column(String(255), index=True)  # Unique ID for this specific call
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # API details
    vendor = Column(String(100), index=True)
    method = Column(String(10), index=True)
    url = Column(Text)
    endpoint = Column(String(500), index=True)

    # Request details
    request_data = Column(JSON)
    request_params = Column(JSON)
    request_headers = Column(JSON)

    # Response details
    status_code = Column(Integer, index=True)
    response_data = Column(JSON)
    response_headers = Column(JSON)

    # Timing
    execution_time_ms = Column(Float, index=True)

    # Context
    account_id = Column(String(255), index=True)
    partner_journey_id = Column(String(255), index=True)
    application_id = Column(String(255), index=True)

    # Error handling
    error_message = Column(Text)
    error_type = Column(String(255))
    circuit_breaker_open = Column(Boolean, default=False)
    fallback_used = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class DatabaseLogger(ABC):
    """
    Abstract base class for database logging backends
    """

    @abstractmethod
    async def log_api_request(self, log_data: Dict[str, Any]) -> bool:
        """Log an API request"""
        pass

    @abstractmethod
    async def log_internal_api_call(self, log_data: Dict[str, Any]) -> bool:
        """Log an internal API call"""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the database connection and tables"""
        pass

    @abstractmethod
    async def close(self):
        """Close database connections"""
        pass


class SQLAlchemyLogger(DatabaseLogger):
    """
    SQLAlchemy-based database logger that works with any SQL database
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.async_session_maker = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the database connection and create tables"""
        try:
            # Create async engine
            if self.database_url.startswith('sqlite'):
                # For SQLite, use aiosqlite
                if not self.database_url.startswith('sqlite+aiosqlite'):
                    self.database_url = self.database_url.replace('sqlite://', 'sqlite+aiosqlite://')
            elif self.database_url.startswith('postgresql'):
                # For PostgreSQL, use asyncpg
                if not self.database_url.startswith('postgresql+asyncpg'):
                    self.database_url = self.database_url.replace('postgresql://', 'postgresql+asyncpg://')
            elif self.database_url.startswith('mysql'):
                # For MySQL, use aiomysql
                if not self.database_url.startswith('mysql+aiomysql'):
                    self.database_url = self.database_url.replace('mysql://', 'mysql+aiomysql://')

            self.engine = create_async_engine(
                self.database_url,
                echo=settings.DEBUG,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            # Create session maker
            self.async_session_maker = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self._initialized = True
            logger.info(
                f"Database logging initialized with {self.database_url.split(':')[0]} backend",
                extra={
                    "event_type": "db_logger_initialized",
                    "backend": self.database_url.split(':')[0],
                    "api_table": settings.API_LOG_TABLE,
                    "internal_api_table": settings.INT_API_LOG_TABLE,
                }
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to initialize database logging: {e}",
                extra={
                    "event_type": "db_logger_init_failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            return False

    async def log_api_request(self, log_data: Dict[str, Any]) -> bool:
        """Log an API request to the database"""

        if not self._initialized:
            logger.warning("Database logger not initialized, skipping log")
            return False

        try:
            async with self.async_session_maker() as session:
                log_entry = APIRequestLog(
                    correlation_id=log_data.get('correlation_id'),
                    request_id=log_data.get('request_id'),
                    timestamp=log_data.get('timestamp', datetime.utcnow()),
                    method=log_data.get('method'),
                    path=log_data.get('path'),
                    url=log_data.get('url'),
                    query_params=log_data.get('query_params'),
                    headers=log_data.get('headers'),
                    body=log_data.get('body'),
                    body_size=log_data.get('body_size'),
                    status_code=log_data.get('status_code'),
                    response_headers=log_data.get('response_headers'),
                    response_body=log_data.get('response_body'),
                    response_size=log_data.get('response_size'),
                    execution_time_ms=log_data.get('execution_time_ms'),
                    client_ip=log_data.get('client_ip'),
                    user_agent=log_data.get('user_agent'),
                    account_id=log_data.get('account_id'),
                    partner_journey_id=log_data.get('partner_journey_id'),
                    application_id=log_data.get('application_id'),
                    user_id=log_data.get('user_id'),
                    error_message=log_data.get('error_message'),
                    error_type=log_data.get('error_type'),
                )

                session.add(log_entry)
                await session.commit()

                logger.debug(
                    "API request logged to database",
                    extra={
                        "event_type": "api_request_logged",
                        "correlation_id": log_data.get('correlation_id'),
                        "request_id": log_data.get('request_id'),
                    }
                )
                return True

        except Exception as e:
            logger.error(
                f"Failed to log API request: {e}",
                extra={
                    "event_type": "api_request_log_failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "correlation_id": log_data.get('correlation_id'),
                }
            )
            return False

    async def log_internal_api_call(self, log_data: Dict[str, Any]) -> bool:
        """Log an internal API call to the database"""

        if not self._initialized:
            logger.warning("Database logger not initialized, skipping log")
            return False

        try:
            async with self.async_session_maker() as session:
                log_entry = InternalAPILog(
                    correlation_id=log_data.get('correlation_id'),
                    parent_request_id=log_data.get('parent_request_id'),
                    call_id=log_data.get('call_id'),
                    timestamp=log_data.get('timestamp', datetime.utcnow()),
                    vendor=log_data.get('vendor'),
                    method=log_data.get('method'),
                    url=log_data.get('url'),
                    endpoint=log_data.get('endpoint'),
                    request_data=log_data.get('request_data'),
                    request_params=log_data.get('request_params'),
                    request_headers=log_data.get('request_headers'),
                    status_code=log_data.get('status_code'),
                    response_data=log_data.get('response_data'),
                    response_headers=log_data.get('response_headers'),
                    execution_time_ms=log_data.get('execution_time_ms'),
                    account_id=log_data.get('account_id'),
                    partner_journey_id=log_data.get('partner_journey_id'),
                    application_id=log_data.get('application_id'),
                    error_message=log_data.get('error_message'),
                    error_type=log_data.get('error_type'),
                    circuit_breaker_open=log_data.get('circuit_breaker_open', False),
                    fallback_used=log_data.get('fallback_used', False),
                )

                session.add(log_entry)
                await session.commit()

                logger.debug(
                    "Internal API call logged to database",
                    extra={
                        "event_type": "internal_api_logged",
                        "correlation_id": log_data.get('correlation_id'),
                        "vendor": log_data.get('vendor'),
                        "call_id": log_data.get('call_id'),
                    }
                )
                return True

        except Exception as e:
            logger.error(
                f"Failed to log internal API call: {e}",
                extra={
                    "event_type": "internal_api_log_failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "correlation_id": log_data.get('correlation_id'),
                }
            )
            return False

    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database logger connections closed")


class LoggingBackendFactory:
    """
    Factory for creating database logging backends based on configuration
    """

    _instance: Optional[DatabaseLogger] = None

    @classmethod
    async def get_logger(cls) -> Optional[DatabaseLogger]:
        """Get or create the database logger instance"""

        if cls._instance is None:
            cls._instance = await cls._create_logger()

        return cls._instance

    @classmethod
    async def _create_logger(cls) -> Optional[DatabaseLogger]:
        """Create the appropriate database logger based on configuration"""

        try:
            database_url = settings.LOG_DB_URL

            if not database_url:
                logger.warning("LOG_DB_URL not configured, database logging disabled")
                return None

            # Create SQLAlchemy logger for any SQL database
            db_logger = SQLAlchemyLogger(database_url)

            # Initialize the logger
            if await db_logger.initialize():
                return db_logger
            else:
                logger.error("Failed to initialize database logger")
                return None

        except Exception as e:
            logger.error(
                f"Failed to create database logger: {e}",
                extra={
                    "event_type": "db_logger_creation_failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            return None

    @classmethod
    async def close(cls):
        """Close the database logger"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None


# Global instance
_db_logger: Optional[DatabaseLogger] = None


async def get_db_logger() -> Optional[DatabaseLogger]:
    """Get the global database logger instance"""
    global _db_logger

    if _db_logger is None:
        _db_logger = await LoggingBackendFactory.get_logger()

    return _db_logger


async def log_api_request(**log_data) -> bool:
    """Convenience function to log an API request"""
    db_logger = await get_db_logger()
    if db_logger:
        return await db_logger.log_api_request(log_data)
    return False


async def log_internal_api_call(**log_data) -> bool:
    """Convenience function to log an internal API call"""
    db_logger = await get_db_logger()
    if db_logger:
        return await db_logger.log_internal_api_call(log_data)
    return False


async def close_db_logger():
    """Close the database logger"""
    await LoggingBackendFactory.close()
