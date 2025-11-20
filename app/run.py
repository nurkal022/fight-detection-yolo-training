"""
Universal Detection System - Flask Application Runner

This application provides a web interface for object detection using YOLO models.
It supports any YOLO model and can be configured to detect specific classes.
"""

import os
import sys

# Add parent directory to path to allow imports
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app import create_app, socketio

# Create Flask app
app = create_app()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Starting Universal Detection System")
    print("="*60)
    print(f"Model: {app.config.get('MODEL_PATH', 'yolo11n.pt')}")
    print(f"Detection Classes: {app.config.get('DETECTION_CLASSES', 'All classes')}")
    print(f"Event Type: {app.config.get('EVENT_TYPE', 'detection')}")
    print(f"Confidence Threshold: {app.config.get('CONFIDENCE_THRESHOLD', 0.5)}")
    print(f"Telegram Enabled: {app.config.get('TELEGRAM_ENABLED', False)}")
    print("="*60 + "\n")
    
    # Run with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=5001,  # Different port from original app
        debug=False,
        allow_unsafe_werkzeug=True
    )


