import json
import logging
import sys
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, get_contextvars

from app.config.settings import settings

# ANSI color codes for console output
COLORS = {
    "DEBUG": "\033[36m",    # Cyan
    "INFO": "\033[32m",     # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",    # Red
    "CRITICAL": "\033[35m", # Magenta
    "RESET": "\033[0m"      # Reset
}


class ColorizedJSONFormatter(logging.Formatter):
    """
    Enhanced JSON formatter with optional console colorization
    """

    def __init__(self, enable_color: bool = True, pretty_print: bool = False):
        super().__init__()
        self.enable_color = enable_color
        self.pretty_print = pretty_print

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON with optional colorization"""

        # Create base log object
        log_object = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Add correlation ID if available
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_object["correlation_id"] = correlation_id

        # Add other context fields
        for field in ["request_id", "account_id", "partner_journey_id", "application_id"]:
            value = getattr(record, field, None)
            if value:
                log_object[field] = value

        # Add exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            log_object["exception"] = {
                "type": exc_type.__name__,
                "message": str(exc_value),
                "traceback": traceback.format_exception(exc_type, exc_value, exc_tb)
            }

        # Add extra fields from the record
        extra_fields = {}
        skip_fields = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "getMessage",
            "exc_info", "exc_text", "stack_info", "correlation_id", "request_id",
            "account_id", "partner_journey_id", "application_id", "message"
        }

        for key, value in record.__dict__.items():
            if key not in skip_fields:
                if isinstance(value, (str, int, float, bool, type(None), list, dict)):
                    extra_fields[key] = value
                else:
                    try:
                        extra_fields[key] = str(value)
                    except Exception:
                        extra_fields[key] = "Non-serializable object"

        if extra_fields:
            log_object["extra"] = extra_fields

        # Format as JSON
        if self.pretty_print:
            json_str = json.dumps(log_object, indent=2, ensure_ascii=False)
        else:
            json_str = json.dumps(log_object, ensure_ascii=False, separators=(',', ':'))

        # Apply colorization if enabled
        if self.enable_color and record.levelname in COLORS:
            color = COLORS[record.levelname]
            reset = COLORS["RESET"]
            return f"{color}{json_str}{reset}"

        return json_str


class PrettyFormatter(logging.Formatter):
    """
    Human-readable formatter with colorization
    """

    def __init__(self, enable_color: bool = True):
        super().__init__()
        self.enable_color = enable_color

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record in a human-readable way"""

        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # Base format
        base_msg = f"[{timestamp}] {record.levelname:8} {record.name}:{record.lineno} - {record.getMessage()}"

        # Add correlation ID if available
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            base_msg += f" [correlation_id={correlation_id}]"

        # Add exception info if present
        if record.exc_info:
            base_msg += "\n" + self.formatException(record.exc_info)

        # Apply colorization if enabled
        if self.enable_color and record.levelname in COLORS:
            color = COLORS[record.levelname]
            reset = COLORS["RESET"]
            return f"{color}{base_msg}{reset}"

        return base_msg


class CorrelationLogger:
    """
    Enhanced logger with correlation ID support and centralized configuration
    """

    def __init__(self, name: str = "app"):
        self.name = name
        self._logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """Setup logger with appropriate formatter based on configuration"""

        # Clear any existing handlers
        self._logger.handlers.clear()

        # Set log level
        log_level = getattr(logging, settings.LOG_LEVEL)
        self._logger.setLevel(log_level)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)

        # Choose formatter based on configuration
        if settings.LOG_FORMAT == "json" or not settings.LOG_PRETTY:
            formatter = ColorizedJSONFormatter(
                enable_color=settings.LOG_COLOR,
                pretty_print=settings.LOG_PRETTY and settings.LOG_FORMAT == "json"
            )
        else:
            formatter = PrettyFormatter(enable_color=settings.LOG_COLOR)

        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        # Prevent propagation to root logger
        self._logger.propagate = False

    def _log(self, level: int, msg: str, *args, **kwargs):
        """Internal logging method that adds correlation context"""

        # Extract extra fields for correlation context
        extra = kwargs.pop('extra', {})

        # Try to get correlation ID from context variables (set by middleware)
        try:
            context = get_contextvars()
            correlation_id = context.get('correlation_id')
            if correlation_id:
                extra['correlation_id'] = correlation_id

            # Add any additional context
            for key in ['request_id', 'account_id', 'partner_journey_id', 'application_id']:
                value = context.get(key)
                if value:
                    extra[key] = value
        except Exception:
            # If structlog context is not available, continue without it
            pass

        kwargs['extra'] = extra
        self._logger._log(level, msg, args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """Log info message"""
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """Log exception with traceback"""
        kwargs['exc_info'] = True
        self.error(msg, *args, **kwargs)

    def set_context(self, **context):
        """Set context for all subsequent log messages in this thread/task"""
        bind_contextvars(**context)

    def clear_context(self):
        """Clear all context variables"""
        clear_contextvars()


# Create the centralized logger instance
logger = CorrelationLogger(name="app")


def get_logger(name: str = "app") -> CorrelationLogger:
    """
    Get a logger instance with correlation support

    Args:
        name: Logger name

    Returns:
        CorrelationLogger instance
    """
    return CorrelationLogger(name=name)


# Correlation ID utilities
def generate_correlation_id() -> str:
    """Generate a new correlation ID"""
    return str(uuid.uuid4())


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context"""
    try:
        return get_contextvars().get('correlation_id')
    except Exception:
        return None


def set_correlation_id(correlation_id: str):
    """Set correlation ID in context"""
    bind_contextvars(correlation_id=correlation_id)


# Legacy compatibility function
def setup_logger(name: str = "app", level: int = logging.INFO) -> CorrelationLogger:
    """
    Legacy function for backward compatibility

    Args:
        name: Logger name
        level: Logging level (ignored - uses settings)

    Returns:
        CorrelationLogger instance
    """
    return get_logger(name)
