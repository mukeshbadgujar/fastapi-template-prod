from typing import List, Optional
from app.common.models import ApiCallLog, AppRequestLog
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
    
    async def log_app_request(self, log_data: AppRequestLog) -> None:
        """Log app request using direct SQLite logging and SQLite logger"""
        from app.utils.direct_logger import log_request_direct
        
        direct_log_success = False
        
        # First try direct SQLite logging
        try:
            direct_log_success = log_request_direct(
                request_id=log_data.request_id,
                endpoint=log_data.endpoint,
                method=log_data.method,
                path=log_data.request_path,
                response=None,  # No response object available here
                status_code=log_data.status_code,
                client_ip=log_data.client_ip,
                user_agent=log_data.user_agent,
                request_query_params=log_data.request_query_params,
                request_body=log_data.request_body,
                request_headers=log_data.request_headers,
                execution_time_ms=log_data.execution_time_ms,
                error_message=log_data.error_message
            )
            if direct_log_success:
                logger.info(f"Successfully logged app request via direct logger: {log_data.endpoint}")
        except Exception as e:
            logger.error(f"Failed to log app request via direct logger: {str(e)}", exc_info=True)
            direct_log_success = False
        
        # If direct logging fails, try using SQLite logger from our list
        if not direct_log_success:
            logger.info("Direct logging failed, trying SQLite logger from loggers list")
            for logger_instance in self._loggers:
                if isinstance(logger_instance, SQLiteLogger):
                    try:
                        # Try the SQLite logger that we initialized in our factory
                        await logger_instance.log_app_request(log_data)
                        logger.info(f"Successfully logged app request via SQLite logger: {log_data.endpoint}")
                        return
                    except Exception as e:
                        logger.error(f"Failed to log app request via SQLite logger: {str(e)}", exc_info=True)
    
    async def close(self) -> None:
        """Close all loggers"""
        for logger_instance in self._loggers:
            try:
                await logger_instance.close()
            except Exception as e:
                logger.error(f"Failed to close {logger_instance.__class__.__name__}: {str(e)}", exc_info=True)
        self._loggers.clear()


# Create a global logger factory for the module
global_logger_factory = DBLoggerFactory() 