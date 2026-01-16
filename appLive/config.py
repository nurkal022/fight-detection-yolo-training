"""
Configuration for Fight Detection Monitoring System
"""
import os
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent

# Model settings
MODEL_PATH = os.environ.get('MODEL_PATH', str(PROJECT_DIR / 'fight_pose_model_export' / 'best.pt'))
CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', 0.5))

# Classes to detect (exclude neutral_class=8)
DETECTION_CLASSES = [0, 1, 2, 3, 4, 5, 6, 7]
CLASS_NAMES = {
    0: 'bent_over',
    1: 'covering_face', 
    2: 'face_slap',
    3: 'fist_clenching',
    4: 'hair_clothes_drag',
    5: 'head_down',
    6: 'head_slap_back',
    7: 'neck_grab',
    8: 'neutral_class'
}

# Camera settings
CAMERA_INDEX = int(os.environ.get('CAMERA_INDEX', 0))
CAMERA_WIDTH = int(os.environ.get('CAMERA_WIDTH', 1280))
CAMERA_HEIGHT = int(os.environ.get('CAMERA_HEIGHT', 720))

# Event filtering settings
EVENT_COOLDOWN = int(os.environ.get('EVENT_COOLDOWN', 30))  # Seconds between same class alerts
EVENT_MIN_DURATION = float(os.environ.get('EVENT_MIN_DURATION', 5.0))  # Min seconds to confirm event
EVENT_MIN_DETECTIONS = int(os.environ.get('EVENT_MIN_DETECTIONS', 3))  # Min detections to confirm
EVENT_TIMEOUT = float(os.environ.get('EVENT_TIMEOUT', 2.0))  # Seconds without detection to end event

# Telegram settings
TELEGRAM_ENABLED = os.environ.get('TELEGRAM_ENABLED', 'True').lower() == 'true'
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8237778300:AAEfUDpqzZkzfvoPtT3ukKYODpD33sxlZv4')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1003207428650')

# Display settings
WINDOW_NAME = "Fight Detection Monitor"
SHOW_FPS = True
SHOW_STATS = True

# Logging
LOG_EVENTS = True
EVENTS_DIR = SCRIPT_DIR / 'events'
