"""
Logging configuration for the application.
"""
import logging
import logging.handlers
import os
import sys
from app.config import settings
from app.middleware.request_id import get_request_id


# Log file path - creates logs directory in project root
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def setup_logging():
    """
    Configure application logging.
    Logs to both console (stdout) and file (logs/app.log).
    """
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(request_id)s - %(message)s'

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))

    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[console_handler, file_handler]
    )

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(RequestIdFilter())
    root_logger.addFilter(RequestIdFilter())

    # Set specific loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)

    logging.info(f"Logging initialized. Log file: {LOG_FILE}")
