"""
Error Handler Module - HOMES-Engine
Handles errors, retries, fallbacks, and structured logging
"""

import logging
import functools
import time
import json
from typing import Any, Callable, Optional, TypeVar, List, Dict
from datetime import datetime
from pathlib import Path
import traceback

# Type definitions
F = TypeVar('F', bound=Callable[..., Any])
T = TypeVar('T')


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
    }
    RESET = '\033[0m'
    
    def format(self, record):
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


def get_logger(name: str, log_file: str = "logs/homes_engine.log") -> logging.Logger:
    """
    Get a structured logger instance
    
    Args:
        name: Logger name (usually __name__)
        log_file: Path to log file
    
    Returns:
        Configured logger instance
    """
    # Ensure logs directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(name)
    
    # Skip if already configured
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # File handler (detailed)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler (colored)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        '%(levelname)s | %(name)s | %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


logger = get_logger(__name__)


class ErrorContext:
    """Context manager for tracking errors and recovery"""
    
    def __init__(self, operation_name: str, max_retries: int = 3):
        self.operation_name = operation_name
        self.max_retries = max_retries
        self.errors: List[Dict] = []
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        logger.info(f"Starting: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        elapsed = (self.end_time - self.start_time).total_seconds()
        
        if exc_type:
            self.add_error(exc_type.__name__, str(exc_val))
            logger.error(
                f"Failed: {self.operation_name} after {elapsed:.2f}s",
                exc_info=(exc_type, exc_val, exc_tb)
            )
            return False
        else:
            logger.info(f"Completed: {self.operation_name} in {elapsed:.2f}s")
            return True
    
    def add_error(self, error_type: str, message: str):
        """Track error occurrence"""
        self.errors.append({
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_summary(self) -> Dict:
        """Get context summary"""
        return {
            "operation": self.operation_name,
            "status": "success" if not self.errors else "failed",
            "errors": self.errors,
            "duration": (self.end_time - self.start_time).total_seconds() if self.end_time else None
        }


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable[[F], F]:
    """
    Decorator for automatic retry with exponential backoff
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay each retry
        exceptions: Tuple of exceptions to catch
    
    Usage:
        @retry(max_attempts=3, delay=1.0)
        def flaky_function():
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"Attempt {attempt}/{max_attempts}: {func.__name__}")
                    return func(*args, **kwargs)
                
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt} failed: {func.__name__} - {str(e)}"
                    )
                    
                    if attempt < max_attempts:
                        logger.debug(f"Waiting {current_delay}s before retry...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
            
            raise last_exception
        
        return wrapper
    
    return decorator


def fallback(
    primary: Callable[..., T],
    fallback_func: Callable[..., T],
    *args,
    **kwargs
) -> T:
    """
    Try primary function, fall back to secondary if it fails
    
    Args:
        primary: Primary function to try
        fallback_func: Function to call if primary fails
        *args: Arguments to pass to functions
        **kwargs: Keyword arguments to pass to functions
    
    Returns:
        Result from either primary or fallback function
    
    Usage:
        result = fallback(
            primary=api_call,
            fallback_func=local_cache_read,
            key="data"
        )
    """
    try:
        logger.debug(f"Trying primary: {primary.__name__}")
        result = primary(*args, **kwargs)
        logger.debug(f"Primary succeeded: {primary.__name__}")
        return result
    
    except Exception as e:
        logger.warning(
            f"Primary failed ({primary.__name__}): {str(e)}, "
            f"trying fallback ({fallback_func.__name__})"
        )
        try:
            result = fallback_func(*args, **kwargs)
            logger.info(f"Fallback succeeded: {fallback_func.__name__}")
            return result
        
        except Exception as fallback_error:
            logger.error(
                f"Both primary and fallback failed: {str(fallback_error)}"
            )
            raise


def with_error_context(operation_name: str):
    """
    Decorator to wrap function with error context
    
    Usage:
        @with_error_context("Script Generation")
        def generate_script():
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ErrorContext(operation_name) as ctx:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    ctx.add_error(type(e).__name__, str(e))
                    raise
        
        return wrapper
    
    return decorator


class ErrorHandler:
    """Centralized error handler for common operations"""
    
    @staticmethod
    def handle_api_error(
        error: Exception,
        api_name: str,
        retry_allowed: bool = True
    ) -> Optional[Any]:
        """
        Handle API-specific errors
        
        Args:
            error: Exception from API call
            api_name: Name of API that failed
            retry_allowed: Whether to suggest retry
        
        Returns:
            Recovery strategy suggestion
        """
        error_msg = str(error)
        error_type = type(error).__name__
        
        logger.error(f"API Error from {api_name}: {error_type} - {error_msg}")
        
        if "timeout" in error_msg.lower():
            logger.info("Detected timeout - suggesting retry with longer timeout")
            return {"strategy": "retry_with_longer_timeout", "api": api_name}
        
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            logger.error(f"Authentication error in {api_name} - check credentials")
            return {"strategy": "check_credentials", "api": api_name}
        
        elif "429" in error_msg or "rate" in error_msg.lower():
            logger.warning(f"Rate limit hit on {api_name} - backing off")
            return {"strategy": "exponential_backoff", "api": api_name}
        
        else:
            logger.warning(f"Unknown API error from {api_name} - attempting fallback")
            return {"strategy": "fallback", "api": api_name}
    
    @staticmethod
    def handle_file_error(error: Exception, file_path: str) -> Optional[Any]:
        """Handle file operation errors"""
        logger.error(f"File error for {file_path}: {str(error)}")
        
        if "not found" in str(error).lower():
            logger.warning(f"File not found: {file_path} - will create")
            return {"strategy": "create_file", "path": file_path}
        
        elif "permission" in str(error).lower():
            logger.error(f"Permission denied for {file_path}")
            return {"strategy": "check_permissions", "path": file_path}
        
        else:
            return {"strategy": "skip_file", "path": file_path}
    
    @staticmethod
    def safe_json_loads(data: str, default: Any = None) -> Any:
        """Safely parse JSON with fallback"""
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {str(e)} - using default")
            return default
    
    @staticmethod
    def log_exception(exc: Exception, context: str = "") -> None:
        """Log full exception with traceback"""
        logger.error(
            f"Exception {context}: {type(exc).__name__}\n"
            f"{traceback.format_exc()}"
        )


# Convenience functions
def log_operation(operation: str, status: str, details: str = ""):
    """Quick logging for operations"""
    if status == "start":
        logger.info(f"▶ {operation}")
    elif status == "success":
        logger.info(f"✅ {operation} {details}")
    elif status == "warning":
        logger.warning(f"⚠️  {operation} {details}")
    elif status == "error":
        logger.error(f"❌ {operation} {details}")
    elif status == "debug":
        logger.debug(f"🔍 {operation} {details}")


if __name__ == "__main__":
    # Example usage
    test_logger = get_logger("test_module")
    test_logger.info("Error handler module loaded successfully")
