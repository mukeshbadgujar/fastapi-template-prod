from typing import List, Optional
from app.common.models import ApiCallLog
from app.common.db_logging.base import BaseDBLogger
from app.common.db_logging.mongo_logger import MongoLogger
from app.common.db_logging.dynamo_logger import DynamoLogger
from app.common.db_logging.sqlite_logger import SQLiteLogger
from app.config.settings import settings
from app.utils.logger import logger


class DBLoggerFactory:
    """Factory for creating and managing database loggers"""
    
    def __init__(self):
        self._loggers: List[BaseDBLogger] = []
        self._initialize_loggers()
    
    def _initialize_loggers(self):
        """Initialize available loggers based on environment settings"""
        loggers_enabled = False
        
        # Initialize MongoDB logger if enabled
        if settings.API_LOG_MONGO_ENABLED and settings.API_LOG_MONGO_URI:
            mongo_logger = MongoLogger()
            if mongo_logger.is_available():
                self._loggers.append(mongo_logger)
                logger.info("MongoDB logger initialized")
                loggers_enabled = True
        
        # Initialize DynamoDB logger if enabled
        if settings.API_LOG_DYNAMODB_ENABLED and settings.API_LOG_DYNAMODB_TABLE:
            dynamo_logger = DynamoLogger()
            if dynamo_logger.is_available():
                self._loggers.append(dynamo_logger)
                logger.info("DynamoDB logger initialized")
                loggers_enabled = True
        
        # Initialize SQLite logger if enabled or if no other loggers are available
        if settings.API_LOG_SQLITE_ENABLED or (settings.API_LOG_FALLBACK_ENABLED and not loggers_enabled):
            sqlite_logger = SQLiteLogger(db_path=settings.API_LOG_SQLITE_PATH)
            self._loggers.append(sqlite_logger)
            if not loggers_enabled and settings.API_LOG_FALLBACK_ENABLED:
                logger.info("SQLite logger initialized as fallback")
            else:
                logger.info("SQLite logger initialized")
    
    async def log_api_call(self, log_data: ApiCallLog) -> None:
        """Log API call using available loggers"""
        for logger_instance in self._loggers:
            try:
                await logger_instance.log_api_call(log_data)
            except Exception as e:
                logger.error(f"Failed to log API call using {logger_instance.__class__.__name__}: {str(e)}", exc_info=True)
    
    async def close(self) -> None:
        """Close all loggers"""
        for logger_instance in self._loggers:
            try:
                await logger_instance.close()
            except Exception as e:
                logger.error(f"Failed to close {logger_instance.__class__.__name__}: {str(e)}", exc_info=True)
        self._loggers.clear() 