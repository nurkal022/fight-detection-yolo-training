import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-other-version')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///detection_system.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Model configuration - Trained fight detection model
    MODEL_PATH = os.environ.get('MODEL_PATH', 'fight_detection/fight_detection_yolo11n2/weights/best.pt')
    CONFIDENCE_THRESHOLD = 0.65  # Increased to reduce false positives
    
    # Detection classes - Exclude neutral_class (8) from detection
    # Only detect fight-related classes: 0-7
    DETECTION_CLASSES = [0, 1, 2, 3, 4, 5, 6, 7]  # Exclude neutral_class (8)
    
    # Event settings
    EVENT_TYPE = os.environ.get('EVENT_TYPE', 'fight_detection')  # Name for your detection type
    EVENT_COOLDOWN = 30  # seconds between same events (increased to reduce false positives)
    EVENT_MIN_DURATION = 2  # minimum duration in seconds to log an event (increased)
    
    # Camera settings
    DEFAULT_CAMERA_INDEX = 0
    FRAME_RATE = 30
    
    # Storage settings
    UPLOAD_FOLDER = 'app/static/uploads'
    EVENTS_FOLDER = 'app/static/events'
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    
    # Recording settings
    SAVE_EVENT_CLIPS = True
    EVENT_CLIP_DURATION = 10  # seconds before and after event
    
    # Alert settings
    ENABLE_ALERTS = True
    ALERT_COOLDOWN = 60  # seconds between alerts for same camera (increased)
    
    # Telegram notifications
    TELEGRAM_ENABLED = True
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8237778300:AAEfUDpqzZkzfvoPtT3ukKYODpD33sxlZv4')
    # Channel: @notifications_from_bot
    # Chat ID: -1003207428650
    # Multiple IDs: comma-separated "id1,id2,id3"
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1003207428650')
    
    # False positive filtering
    MIN_DETECTION_COUNT = 3  # Minimum number of detections in event to trigger notification
    MIN_CONFIDENCE_FOR_ALERT = 0.5  # Minimum confidence to send Telegram alert
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'app/logs/app.log'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///detection_system.db')


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


