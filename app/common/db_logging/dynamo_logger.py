import boto3

from app.common.db_logging.base import BaseDBLogger
from app.config.settings import settings
from app.models.models_request_response import ApiCallLog
from app.utils.logger import logger


class DynamoLogger(BaseDBLogger):
    """DynamoDB logger implementation"""

    def __init__(self):
        self._client = None
        self._table = None

    def is_available(self) -> bool:
        """Check if DynamoDB is configured"""
        return bool(settings.API_LOG_DYNAMODB_TABLE)

    def _get_client(self):
        """Get or create DynamoDB client"""
        if self._client is None and self.is_available():
            self._client = boto3.resource('dynamodb')
            self._table = self._client.Table(settings.API_LOG_DYNAMODB_TABLE)
        return self._client

    async def log_api_call(self, log_data: ApiCallLog) -> None:
        """Log API call to DynamoDB"""
        try:
            if client := self._get_client():
                log_dict = log_data.model_dump(exclude_none=True)
                log_dict["timestamp"] = log_dict["timestamp"].isoformat()
                self._table.put_item(Item=log_dict)
                logger.info(f"Logged API call to DynamoDB: {log_data.endpoint}")
        except Exception as e:
            logger.error(f"Failed to log API call to DynamoDB: {str(e)}", exc_info=True)

    async def close(self) -> None:
        """Close DynamoDB connection"""
        if self._client:
            self._client = None
            self._table = None
