from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from app.models.models_request_response import ApiCallLog, AppRequestLog


class BaseDBLogger(ABC):
    """Base class for database loggers"""

    @abstractmethod
    async def log_api_call(self, log_data: ApiCallLog) -> None:
        """Log API call to database"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close database connection"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if logger is available"""
        pass

    async def log_app_request(self, log_data: AppRequestLog) -> None:
        """Log application request to database - optional implementation"""
        pass
