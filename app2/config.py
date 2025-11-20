"""
Configuration for standalone detection display application
"""
import os

# Model settings - relative to app2 directory
_MODEL_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                              'fight_detection/fight_detection_yolo11n2/weights/best.pt')
MODEL_PATH = os.environ.get('MODEL_PATH', _MODEL_DEFAULT)
CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', 0.65))
DETECTION_CLASSES = [0, 1, 2, 3, 4, 5, 6, 7]  # Exclude neutral_class (8)

# Camera settings
CAMERA_INDEX = int(os.environ.get('CAMERA_INDEX', 0))
CAMERA_WIDTH = int(os.environ.get('CAMERA_WIDTH', 1920))
CAMERA_HEIGHT = int(os.environ.get('CAMERA_HEIGHT', 1080))

# Display settings
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 30
FULLSCREEN = False

# Colors (RGB)
COLORS = {
    'background': (20, 20, 20),
    'text': (255, 255, 255),
    'detection_box': (0, 255, 0),
    'detection_text': (255, 255, 0),
    'alert': (255, 0, 0),
    'info': (100, 150, 255),
    'success': (0, 255, 100),
}

# Detection settings
SHOW_DETECTION_BOXES = True
SHOW_STATS = True
ALERT_SOUND_ENABLED = True
ALERT_SOUND_FILE = None  # Path to sound file, or None for beep

# Notification settings
NOTIFICATIONS_ENABLED = True
NOTIFICATION_DURATION = 5  # seconds

# Telegram notifications
# Channel: @notifications_from_bot
# Chat ID: -1003207428650
# Multiple IDs: comma-separated "id1,id2,id3"
TELEGRAM_ENABLED = os.environ.get('TELEGRAM_ENABLED', 'True').lower() == 'true'
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8237778300:AAEfUDpqzZkzfvoPtT3ukKYODpD33sxlZv4')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1003207428650')

# Event settings - reduced for more frequent notifications
EVENT_COOLDOWN = 10  # seconds between same events (reduced from 30)
EVENT_MIN_DURATION = 0.5  # minimum duration in seconds to log an event (reduced from 2)

# Font settings
FONT_SIZE_SMALL = 16
FONT_SIZE_MEDIUM = 24
FONT_SIZE_LARGE = 32
