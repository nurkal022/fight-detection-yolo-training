#!/usr/bin/env python3
"""
Main entry point for standalone detection display application
"""
import sys
import os
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detector_display import DetectionDisplay
from config import CAMERA_INDEX, MODEL_PATH


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Standalone Fight Detection Display')
    parser.add_argument('--camera', type=int, default=CAMERA_INDEX, help=f'Camera index (default: {CAMERA_INDEX})')
    parser.add_argument('--model', type=str, default=MODEL_PATH, help=f'Model path (default: {MODEL_PATH})')
    parser.add_argument('--fullscreen', action='store_true', help='Start in fullscreen mode')
    parser.add_argument('--list-cameras', action='store_true', help='List available cameras')
    
    args = parser.parse_args()
    
    # List cameras if requested
    if args.list_cameras:
        import cv2
        print("\nChecking available cameras...")
        available = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    h, w = frame.shape[:2]
                    available.append((i, w, h))
                    print(f"  Camera {i}: {w}x{h}")
                cap.release()
        if not available:
            print("  No cameras found")
        print()
        return
    
    # Update config if needed
    if args.fullscreen:
        import config
        config.FULLSCREEN = True
    
    if args.model != MODEL_PATH:
        import config
        config.MODEL_PATH = args.model
    
    # Check if model exists
    if not os.path.exists(args.model):
        print(f"Error: Model file not found: {args.model}")
        print(f"Please check MODEL_PATH in config.py or use --model option")
        sys.exit(1)
    
    # Create and run display
    print(f"Starting standalone detection display...")
    print(f"Camera: {args.camera}")
    print(f"Model: {args.model}")
    
    try:
        app = DetectionDisplay(args.camera)
        app.run()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
