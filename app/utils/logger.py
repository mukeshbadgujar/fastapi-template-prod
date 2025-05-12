import json
import logging
import sys
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from app.config.settings import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string
        """
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        
        # Extract request_id if available
        request_id = getattr(record, "request_id", str(uuid.uuid4()))
        
        # Extract partner_journey_id if available
        partner_journey_id = getattr(record, "partner_journey_id", "")
        
        # Extract account_id if available
        account_id = getattr(record, "account_id", "")
        
        # Extract application_id if available
        application_id = getattr(record, "application_id", "")
        
        # Create the JSON log object with standard fields
        log_object = {
            "asctime": timestamp,
            "levelname": record.levelname,
            "name": record.name,
            "filename": record.filename,
            "funcName": record.funcName,
            "lineno": record.lineno,
            "message": record.getMessage(),
            "request_id": request_id
        }
        
        # Add optional fields if they have values
        if partner_journey_id:
            log_object["partner_journey_id"] = partner_journey_id
        
        if account_id:
            log_object["account_id"] = account_id
            
        if application_id:
            log_object["application_id"] = application_id
        
        # Check if exception info exists
        if record.exc_info:
            exception_type, exception_value, exception_tb = record.exc_info
            log_object["exception"] = {
                "type": exception_type.__name__,
                "message": str(exception_value),
                "traceback": traceback.format_exception(exception_type, exception_value, exception_tb)
            }
        
        # Add extra fields from record.__dict__
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename", 
                          "funcName", "levelname", "levelno", "lineno", "module", 
                          "msecs", "message", "msg", "name", "pathname", "process", 
                          "processName", "relativeCreated", "stack_info", "thread", "threadName",
                          "request_id", "partner_journey_id", "account_id", "application_id"]:
                if isinstance(value, (str, int, float, bool, type(None), list, dict)):
                    log_object[key] = value
                else:
                    # Convert non-serializable objects to string
                    try:
                        log_object[key] = str(value)
                    except:
                        log_object[key] = "Non-serializable object"
        
        return json.dumps(log_object)


class CustomLogger(logging.Logger):
    """
    Custom logger class with additional context fields
    """
    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)
        self.request_id = None
        self.partner_journey_id = None
        self.account_id = None
        self.application_id = None
    
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        """
        Override _log to add request_id and other context fields
        """
        if extra is None:
            extra = {}
        
        # Add context fields if they're set and not in extra
        if hasattr(self, 'request_id') and self.request_id and 'request_id' not in extra:
            extra['request_id'] = self.request_id
            
        if hasattr(self, 'partner_journey_id') and self.partner_journey_id and 'partner_journey_id' not in extra:
            extra['partner_journey_id'] = self.partner_journey_id
            
        if hasattr(self, 'account_id') and self.account_id and 'account_id' not in extra:
            extra['account_id'] = self.account_id
            
        if hasattr(self, 'application_id') and self.application_id and 'application_id' not in extra:
            extra['application_id'] = self.application_id
        
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
    
    def set_context(self, 
                    request_id: Optional[str] = None, 
                    partner_journey_id: Optional[str] = None,
                    account_id: Optional[str] = None,
                    application_id: Optional[str] = None):
        """
        Set context fields for all subsequent log messages
        """
        if request_id:
            self.request_id = request_id
            
        if partner_journey_id:
            self.partner_journey_id = partner_journey_id
            
        if account_id:
            self.account_id = account_id
            
        if application_id:
            self.application_id = application_id


# Register our custom logger class
logging.setLoggerClass(CustomLogger)


def setup_logger(name: str = "app", level: int = logging.INFO) -> CustomLogger:
    """
    Setup a logger with handlers and formatters
    
    Args:
        name: Logger name
        level: Logging level
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    
    # Add handler to logger if it doesn't already have one
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    # Make sure logger doesn't propagate to root logger
    logger.propagate = False
    
    return logger


# Create a default logger instance
logger = setup_logger(level=logging.DEBUG if settings.DEBUG else logging.INFO)
