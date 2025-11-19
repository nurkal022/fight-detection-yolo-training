import logging
import os
from datetime import datetime
from flask import has_app_context

# Create logs directory
os.makedirs('app/logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app/logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('detection_system')


def log_system(level, message, module=None, camera_id=None):
    """
    Log system events and optionally save to database.
    
    Args:
        level: Log level (INFO, WARNING, ERROR)
        message: Log message
        module: Module name
        camera_id: Optional camera ID
    """
    log_message = f"[{module}] {message}" if module else message
    
    # Log to file
    if level == 'INFO':
        logger.info(log_message)
    elif level == 'WARNING':
        logger.warning(log_message)
    elif level == 'ERROR':
        logger.error(log_message)
    
    # Save to database if app context is available
    if has_app_context():
        try:
            from app import db
            from app.models import SystemLog
            
            log_entry = SystemLog(
                level=level,
                message=message,
                module=module,
                camera_id=camera_id
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to save log to database: {str(e)}")


def get_logger(name):
    """Get a logger instance for a specific module."""
    return logging.getLogger(f'detection_system.{name}')


