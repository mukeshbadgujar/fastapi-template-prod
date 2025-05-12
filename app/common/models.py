from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel


# Status of API call
class ApiStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


# API Call Log Model
class ApiCallLog(BaseModel):
    """
    Model for API call logging
    """
    request_id: str
    endpoint: str
    method: str
    partner_journey_id: Optional[str] = None
    account_id: Optional[str] = None
    application_id: Optional[str] = None
    request_body: Optional[Dict[str, Any]] = None
    request_headers: Dict[str, str] = {}
    response_body: Optional[Dict[str, Any]] = None
    response_headers: Dict[str, str] = {}
    status_code: Optional[int] = None
    status: ApiStatus
    execution_time_ms: float
    error_message: Optional[str] = None
    timestamp: datetime = datetime.now()
    vendor: Optional[str] = None
    fallback_used: bool = False 