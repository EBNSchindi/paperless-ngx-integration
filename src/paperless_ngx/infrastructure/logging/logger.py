"""Structured logging framework with proper formatters and handlers.

This module provides comprehensive logging with rotation, multiple handlers,
and request ID tracking for better debugging.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import structlog
from pythonjsonlogger import jsonlogger

from src.paperless_ngx.infrastructure.config.settings import get_settings

# Context variable for request ID tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    """Add request ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id to the log record.
        
        Args:
            record: Log record to filter
            
        Returns:
            Always True to keep the record
        """
        record.request_id = request_id_var.get() or "no-request-id"
        return True


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs."""
    
    SENSITIVE_PATTERNS = [
        ("Token ", "Token [MASKED]"),
        ("Bearer ", "Bearer [MASKED]"),
        ("api_key=", "api_key=[MASKED]"),
        ("password=", "password=[MASKED]"),
        ("secret=", "secret=[MASKED]"),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in log messages.
        
        Args:
            record: Log record to filter
            
        Returns:
            Always True to keep the record
        """
        if hasattr(record, "msg"):
            msg = str(record.msg)
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                if pattern in msg:
                    msg = msg.replace(pattern + msg.split(pattern)[1].split()[0], replacement)
            record.msg = msg
        
        if hasattr(record, "args") and record.args:
            args = []
            for arg in record.args:
                arg_str = str(arg)
                for pattern, replacement in self.SENSITIVE_PATTERNS:
                    if pattern in arg_str:
                        arg_str = arg_str.replace(
                            pattern + arg_str.split(pattern)[1].split()[0],
                            replacement
                        )
                args.append(arg_str)
            record.args = tuple(args)
        
        return True


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log string with colors
        """
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # Format the message
        result = super().format(record)
        
        # Reset level name for other handlers
        record.levelname = levelname
        
        return result


class LoggerSetup:
    """Setup and configure application logging."""
    
    def __init__(self, settings: Optional[Any] = None):
        """Initialize logger setup.
        
        Args:
            settings: Optional settings object, uses get_settings() if None
        """
        self.settings = settings or get_settings()
        self.loggers: Dict[str, logging.Logger] = {}
        self._setup_complete = False
        
    def setup(self) -> None:
        """Setup logging configuration."""
        if self._setup_complete:
            return
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.settings.log_level))
        
        # Clear existing handlers
        root_logger.handlers = []
        
        # Add filters
        request_id_filter = RequestIdFilter()
        sensitive_data_filter = SensitiveDataFilter()
        
        # Setup console handler
        console_handler = self._create_console_handler()
        console_handler.addFilter(request_id_filter)
        console_handler.addFilter(sensitive_data_filter)
        root_logger.addHandler(console_handler)
        
        # Setup file handler if configured
        if self.settings.log_file:
            file_handler = self._create_file_handler()
            file_handler.addFilter(request_id_filter)
            file_handler.addFilter(sensitive_data_filter)
            root_logger.addHandler(file_handler)
        
        # Setup structured logging with structlog
        self._setup_structlog()
        
        # Adjust third-party library logging levels
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("litellm").setLevel(logging.INFO)
        logging.getLogger("openai").setLevel(logging.WARNING)
        
        self._setup_complete = True
        
    def _create_console_handler(self) -> logging.StreamHandler:
        """Create console handler with colored output.
        
        Returns:
            Configured console handler
        """
        handler = logging.StreamHandler(sys.stdout)
        
        # Use colored formatter for TTY, plain for non-TTY (e.g., logs)
        if sys.stdout.isatty():
            formatter = ColoredFormatter(self.settings.log_format)
        else:
            formatter = logging.Formatter(self.settings.log_format)
        
        handler.setFormatter(formatter)
        handler.setLevel(getattr(logging, self.settings.log_level))
        
        return handler
    
    def _create_file_handler(self) -> logging.handlers.RotatingFileHandler:
        """Create rotating file handler with JSON formatting.
        
        Returns:
            Configured file handler
        """
        # Ensure log directory exists
        log_file = Path(self.settings.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=self.settings.log_rotation_size,
            backupCount=self.settings.log_backup_count,
            encoding="utf-8"
        )
        
        # Use JSON formatter for file logs
        json_formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(request_id)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
            timestamp=True
        )
        
        handler.setFormatter(json_formatter)
        handler.setLevel(getattr(logging, self.settings.log_level))
        
        return handler
    
    def _setup_structlog(self) -> None:
        """Configure structlog for structured logging."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                self._add_request_id,
                structlog.dev.ConsoleRenderer() if sys.stdout.isatty() else structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    @staticmethod
    def _add_request_id(logger, method_name, event_dict):
        """Add request ID to structlog events.
        
        Args:
            logger: Logger instance
            method_name: Method name
            event_dict: Event dictionary
            
        Returns:
            Modified event dictionary
        """
        request_id = request_id_var.get()
        if request_id:
            event_dict["request_id"] = request_id
        return event_dict
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger instance.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Configured logger instance
        """
        if not self._setup_complete:
            self.setup()
        
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        
        return self.loggers[name]
    
    def get_struct_logger(self, name: str) -> structlog.BoundLogger:
        """Get a structured logger instance.
        
        Args:
            name: Logger name
            
        Returns:
            Structured logger instance
        """
        if not self._setup_complete:
            self.setup()
        
        return structlog.get_logger(name)


class RequestContext:
    """Context manager for request ID tracking."""
    
    def __init__(self, request_id: Optional[str] = None):
        """Initialize request context.
        
        Args:
            request_id: Optional request ID, generates UUID if None
        """
        self.request_id = request_id or str(uuid.uuid4())
        self.token = None
        
    def __enter__(self):
        """Enter context and set request ID."""
        self.token = request_id_var.set(self.request_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and reset request ID."""
        if self.token:
            request_id_var.reset(self.token)


class LoggingMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class.
        
        Returns:
            Logger instance
        """
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__module__)
        return self._logger
    
    @property
    def struct_logger(self) -> structlog.BoundLogger:
        """Get structured logger for this class.
        
        Returns:
            Structured logger instance
        """
        if not hasattr(self, "_struct_logger"):
            self._struct_logger = get_struct_logger(self.__class__.__module__)
        return self._struct_logger
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message with context.
        
        Args:
            message: Log message
            **kwargs: Additional context
        """
        self.struct_logger.debug(message, **kwargs)
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log info message with context.
        
        Args:
            message: Log message
            **kwargs: Additional context
        """
        self.struct_logger.info(message, **kwargs)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message with context.
        
        Args:
            message: Log message
            **kwargs: Additional context
        """
        self.struct_logger.warning(message, **kwargs)
    
    def log_error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log error message with context.
        
        Args:
            message: Log message
            exc_info: Include exception info
            **kwargs: Additional context
        """
        self.struct_logger.error(message, exc_info=exc_info, **kwargs)
    
    def log_critical(self, message: str, exc_info: bool = True, **kwargs) -> None:
        """Log critical message with context.
        
        Args:
            message: Log message
            exc_info: Include exception info
            **kwargs: Additional context
        """
        self.struct_logger.critical(message, exc_info=exc_info, **kwargs)


# Singleton instance
_logger_setup: Optional[LoggerSetup] = None


def setup_logging(settings: Optional[Any] = None) -> LoggerSetup:
    """Setup application logging.
    
    Args:
        settings: Optional settings object
        
    Returns:
        LoggerSetup instance
    """
    global _logger_setup
    
    if _logger_setup is None:
        _logger_setup = LoggerSetup(settings)
        _logger_setup.setup()
    
    return _logger_setup


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    if _logger_setup is None:
        setup_logging()
    
    return _logger_setup.get_logger(name)


def get_struct_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Structured logger instance
    """
    if _logger_setup is None:
        setup_logging()
    
    return _logger_setup.get_struct_logger(name)


def log_function_call(func):
    """Decorator to log function calls with timing.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_struct_logger(func.__module__)
        start_time = time.time()
        
        logger.debug(
            f"Calling {func.__name__}",
            function=func.__name__,
            module=func.__module__
        )
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            logger.debug(
                f"Completed {func.__name__}",
                function=func.__name__,
                module=func.__module__,
                elapsed_time=elapsed
            )
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            
            logger.error(
                f"Failed {func.__name__}",
                function=func.__name__,
                module=func.__module__,
                elapsed_time=elapsed,
                error=str(e),
                exc_info=True
            )
            
            raise
    
    return wrapper