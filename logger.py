import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from datetime import datetime
from contextlib import contextmanager
import inspect

class Logger:
    """Comprehensive logging system for the project"""
    
    _logger = None
    _max_log_size = 10 * 1024 * 1024  # 10 MB
    _backup_count = 5
    
    @classmethod
    def _get_log_file(cls):
        """Get log file path based on calling script name"""
        # Get the frame of the caller
        frame = inspect.currentframe()
        try:
            # Walk up the stack to find the first non-logger call
            while frame:
                if frame.f_globals.get('__name__') != __name__:
                    script_path = frame.f_globals.get('__file__', 'unknown_script')
                    script_name = os.path.splitext(os.path.basename(script_path))[0]
                    return os.path.join(os.getcwd(), f"{script_name}.log")
                frame = frame.f_back
            return os.path.join(os.getcwd(), "application.log")
        finally:
            del frame  # Avoid reference cycles
    
    @classmethod
    def initialize(cls, debug=False, log_file=None):
        """Initialize the logging system"""
        if cls._logger is None:
            cls._logger = logging.getLogger("promed_taps")
            cls._logger.setLevel(logging.DEBUG if debug else logging.INFO)
            
            # Clear existing handlers
            cls._logger.handlers.clear()
            
            # Determine log file path
            file_path = log_file if log_file else cls._get_log_file()
            
            # File handler with rotation
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=cls._max_log_size,
                backupCount=cls._backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            cls._logger.addHandler(file_handler)
            
            # Console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            cls._logger.addHandler(console_handler)
            
            cls.debug(f"Logger initialized (logging to {file_path})")


# class Logger:
#     """Comprehensive logging system for the project"""
    
#     _logger = None
#     _log_file = os.path.join(os.getcwd(), "promed_taps.log")
#     _max_log_size = 10 * 1024 * 1024  # 10 MB
#     _backup_count = 5
    
#     @classmethod
#     def initialize(cls, debug=False):
#         """Initialize the logging system"""
#         if cls._logger is None:
#             cls._logger = logging.getLogger("promed_taps")
#             cls._logger.setLevel(logging.DEBUG if debug else logging.INFO)
            
#             # Clear existing handlers
#             cls._logger.handlers.clear()
            
#             # File handler with rotation
#             file_handler = RotatingFileHandler(
#                 cls._log_file,
#                 maxBytes=cls._max_log_size,
#                 backupCount=cls._backup_count,
#                 encoding='utf-8'
#             )
#             file_handler.setFormatter(logging.Formatter(
#                 '%(asctime)s - %(levelname)s - %(message)s'
#             ))
#             cls._logger.addHandler(file_handler)
            
#             # Console handler
#             console_handler = logging.StreamHandler(sys.stdout)
#             console_handler.setFormatter(logging.Formatter(
#                 '%(asctime)s - %(levelname)s - %(message)s'
#             ))
#             cls._logger.addHandler(console_handler)
            
#             cls.debug("Logger initialized")
    
    @classmethod
    @contextmanager
    def temporary_level(cls, level):
        """Temporarily change log level within a context"""
        original_level = cls._logger.level
        cls._logger.setLevel(level)
        try:
            yield
        finally:
            cls._logger.setLevel(original_level)
    
    @classmethod
    def debug(cls, message, *args, **kwargs):
        """Log debug message"""
        cls._log(logging.DEBUG, message, *args, **kwargs)
    
    @classmethod
    def info(cls, message, *args, **kwargs):
        """Log info message"""
        cls._log(logging.INFO, message, *args, **kwargs)
    
    @classmethod
    def warning(cls, message, *args, **kwargs):
        """Log warning message"""
        cls._log(logging.WARNING, message, *args, **kwargs)
    
    @classmethod
    def error(cls, message, *args, **kwargs):
        """Log error message"""
        cls._log(logging.ERROR, message, *args, **kwargs)
    
    @classmethod
    def critical(cls, message, *args, **kwargs):
        """Log critical message"""
        cls._log(logging.CRITICAL, message, *args, **kwargs)
    
    @classmethod
    def exception(cls, message, *args, **kwargs):
        """Log exception with stack trace"""
        cls._logger.exception(message, *args, **kwargs)
    
    @classmethod
    def _log(cls, level, message, *args, **kwargs):
        """Internal logging method"""
        if cls._logger is None:
            cls.initialize()
        
        # Add timestamp and thread info if needed
        extra = kwargs.get('extra', {})
        extra['timestamp'] = datetime.now().isoformat()
        kwargs['extra'] = extra
        
        cls._logger.log(level, message, *args, **kwargs)
    
    @classmethod
    def log_operation(cls, operation_name, debug=False):
        """Decorator to log function execution with optional debug level"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                log_level = logging.DEBUG if debug else logging.INFO
                cls._log(log_level, f"Starting operation: {operation_name}")
                start_time = datetime.now()
                try:
                    result = func(*args, **kwargs)
                    duration = (datetime.now() - start_time).total_seconds()
                    cls._log(log_level, f"Completed operation: {operation_name} (took {duration:.2f}s)")
                    return result
                except Exception as e:
                    duration = (datetime.now() - start_time).total_seconds()
                    cls.error(f"Failed operation: {operation_name} after {duration:.2f}s - {str(e)}")
                    raise
            return wrapper
        return decorator




# import logging
# from logging.handlers import RotatingFileHandler
# import os
# import sys
# from datetime import datetime

# class Logger:
#     """Comprehensive logging system for the project"""
    
#     _logger = None
#     _log_file = os.path.join(os.getcwd(), "promed_taps.log")
#     _max_log_size = 10 * 1024 * 1024  # 10 MB
#     _backup_count = 5
    
#     @classmethod
#     def initialize(cls, debug=False):
#         """Initialize the logging system"""
#         if cls._logger is None:
#             cls._logger = logging.getLogger("promed_taps")
#             cls._logger.setLevel(logging.DEBUG if debug else logging.INFO)
            
#             # Clear existing handlers
#             cls._logger.handlers.clear()
            
#             # File handler with rotation
#             file_handler = RotatingFileHandler(
#                 cls._log_file,
#                 maxBytes=cls._max_log_size,
#                 backupCount=cls._backup_count,
#                 encoding='utf-8'
#             )
#             file_handler.setFormatter(logging.Formatter(
#                 '%(asctime)s - %(levelname)s - %(message)s'
#             ))
#             cls._logger.addHandler(file_handler)
            
#             # Console handler
#             console_handler = logging.StreamHandler(sys.stdout)
#             console_handler.setFormatter(logging.Formatter(
#                 '%(asctime)s - %(levelname)s - %(message)s'
#             ))
#             cls._logger.addHandler(console_handler)
            
#             cls.debug("Logger initialized")
    
#     @classmethod
#     def debug(cls, message, *args, **kwargs):
#         """Log debug message"""
#         cls._log(logging.DEBUG, message, *args, **kwargs)
    
#     @classmethod
#     def info(cls, message, *args, **kwargs):
#         """Log info message"""
#         cls._log(logging.INFO, message, *args, **kwargs)
    
#     @classmethod
#     def warning(cls, message, *args, **kwargs):
#         """Log warning message"""
#         cls._log(logging.WARNING, message, *args, **kwargs)
    
#     @classmethod
#     def error(cls, message, *args, **kwargs):
#         """Log error message"""
#         cls._log(logging.ERROR, message, *args, **kwargs)
    
#     @classmethod
#     def critical(cls, message, *args, **kwargs):
#         """Log critical message"""
#         cls._log(logging.CRITICAL, message, *args, **kwargs)
    
#     @classmethod
#     def exception(cls, message, *args, **kwargs):
#         """Log exception with stack trace"""
#         cls._logger.exception(message, *args, **kwargs)
    
#     @classmethod
#     def _log(cls, level, message, *args, **kwargs):
#         """Internal logging method"""
#         if cls._logger is None:
#             cls.initialize()
        
#         # Add timestamp and thread info if needed
#         extra = kwargs.get('extra', {})
#         extra['timestamp'] = datetime.now().isoformat()
#         kwargs['extra'] = extra
        
#         cls._logger.log(level, message, *args, **kwargs)
    
#     @classmethod
#     def log_operation(cls, operation_name):
#         """Decorator to log function execution"""
#         def decorator(func):
#             def wrapper(*args, **kwargs):
#                 cls.info(f"Starting operation: {operation_name}")
#                 start_time = datetime.now()
#                 try:
#                     result = func(*args, **kwargs)
#                     duration = (datetime.now() - start_time).total_seconds()
#                     cls.info(f"Completed operation: {operation_name} (took {duration:.2f}s)")
#                     return result
#                 except Exception as e:
#                     duration = (datetime.now() - start_time).total_seconds()
#                     cls.error(f"Failed operation: {operation_name} after {duration:.2f}s - {str(e)}")
#                     raise
#             return wrapper
#         return decorator