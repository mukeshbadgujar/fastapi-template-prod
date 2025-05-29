import pymongo

from app.common.db_logging.base import BaseDBLogger
from app.config.settings import settings
from app.models.models_request_response import ApiCallLog
from app.utils.logger import logger


class MongoLogger(BaseDBLogger):
    """MongoDB logger implementation"""

    def __init__(self):
        self._client = None
        self._db = None
        self._collection = None

    def is_available(self) -> bool:
        """Check if MongoDB is configured"""
        return bool(settings.API_LOG_MONGO_URI)

    def _get_client(self):
        """Get or create MongoDB client"""
        if self._client is None and self.is_available():
            self._client = pymongo.MongoClient(settings.API_LOG_MONGO_URI)
            self._db = self._client.api_logs
            self._collection = self._db.api_calls
        return self._client

    async def log_api_call(self, log_data: ApiCallLog) -> None:
        """Log API call to MongoDB"""
        try:
            if client := self._get_client():
                log_dict = log_data.model_dump(exclude_none=True)
                self._collection.insert_one(log_dict)
                logger.info(f"Logged API call to MongoDB: {log_data.endpoint}")
        except Exception as e:
            logger.error(f"Failed to log API call to MongoDB: {str(e)}", exc_info=True)

    async def close(self) -> None:
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._collection = None
