import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-other-version')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///detection_system.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Model configuration - CHANGE THIS FOR YOUR MODEL
    MODEL_PATH = os.environ.get('MODEL_PATH', 'yolo11n.pt')  # Default YOLO model
    CONFIDENCE_THRESHOLD = 0.5
    
    # Detection classes - CONFIGURE YOUR CLASSES HERE
    # Example: ['person', 'car', 'dog'] or class indices [0, 1, 2]
    DETECTION_CLASSES = None  # None = all classes, or specify list of class names/indices
    
    # Event settings
    EVENT_TYPE = os.environ.get('EVENT_TYPE', 'detection')  # Name for your detection type
    EVENT_COOLDOWN = 5  # seconds between same events
    EVENT_MIN_DURATION = 1  # minimum duration to log an event
    
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
    ALERT_COOLDOWN = 30  # seconds between alerts for same camera
    
    # Telegram notifications
    TELEGRAM_ENABLED = True
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8266725905:AAHXFOUpOOkv4lTNQw9JAH8CDpXuKGxNFZE')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '889928782')  # Single chat ID or comma-separated: "123,456,789"
    
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


