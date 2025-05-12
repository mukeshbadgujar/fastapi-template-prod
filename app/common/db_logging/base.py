from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from app.common.models import ApiCallLog


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