#!/usr/bin/env python3
"""
Fight Detection Monitoring System
Live camera monitoring with Telegram notifications
"""

import cv2
import time
import argparse
import requests
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from ultralytics import YOLO

from config import (
    MODEL_PATH, CONFIDENCE_THRESHOLD, DETECTION_CLASSES, CLASS_NAMES,
    CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT,
    EVENT_COOLDOWN, EVENT_MIN_DURATION, EVENT_MIN_DETECTIONS, EVENT_TIMEOUT,
    TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    WINDOW_NAME, SHOW_FPS, SHOW_STATS, LOG_EVENTS, EVENTS_DIR
)


class EventManager:
    """Manages detection events with cooldown and duplicate filtering."""
    
    def __init__(self, cooldown=30, min_duration=1.0, min_detections=3, timeout=2.0):
        self.cooldown = cooldown
        self.min_duration = min_duration
        self.min_detections = min_detections
        self.timeout = timeout
        
        # Active events per class
        self.active_events = {}  # class_id -> event_data
        self.last_alert_time = {}  # class_id -> timestamp
        
    def process_detections(self, detections, frame=None):
        """
        Process detections and return confirmed events.
        
        Args:
            detections: List of (class_id, confidence, bbox) tuples
            frame: Current frame for saving
            
        Returns:
            List of confirmed events ready for notification
        """
        current_time = time.time()
        confirmed_events = []
        detected_classes = set()
        
        # Group detections by class
        class_detections = defaultdict(list)
        for class_id, confidence, bbox in detections:
            if class_id in DETECTION_CLASSES:
                class_detections[class_id].append((confidence, bbox))
                detected_classes.add(class_id)
        
        # Update active events
        for class_id, dets in class_detections.items():
            max_conf = max(d[0] for d in dets)
            best_bbox = max(dets, key=lambda x: x[0])[1]
            
            if class_id not in self.active_events:
                # Start new event
                self.active_events[class_id] = {
                    'class_id': class_id,
                    'class_name': CLASS_NAMES.get(class_id, f'class_{class_id}'),
                    'start_time': current_time,
                    'last_detection': current_time,
                    'max_confidence': max_conf,
                    'detection_count': len(dets),
                    'best_frame': frame.copy() if frame is not None else None,
                    'bbox': best_bbox
                }
            else:
                # Update existing event
                event = self.active_events[class_id]
                event['last_detection'] = current_time
                event['detection_count'] += len(dets)
                if max_conf > event['max_confidence']:
                    event['max_confidence'] = max_conf
                    event['best_frame'] = frame.copy() if frame is not None else None
                    event['bbox'] = best_bbox
        
        # Check for event completion (timeout or confirmation)
        classes_to_remove = []
        for class_id, event in self.active_events.items():
            time_since_last = current_time - event['last_detection']
            duration = current_time - event['start_time']
            
            # Event timed out - check if it should be confirmed
            if time_since_last >= self.timeout or class_id not in detected_classes:
                if duration >= self.min_duration and event['detection_count'] >= self.min_detections:
                    # Check cooldown
                    last_alert = self.last_alert_time.get(class_id, 0)
                    if current_time - last_alert >= self.cooldown:
                        # Confirm event
                        event['end_time'] = current_time
                        event['duration'] = duration
                        confirmed_events.append(event)
                        self.last_alert_time[class_id] = current_time
                
                classes_to_remove.append(class_id)
        
        # Remove completed/timed-out events
        for class_id in classes_to_remove:
            del self.active_events[class_id]
        
        return confirmed_events
    
    def get_active_events_info(self):
        """Get info about currently active events."""
        current_time = time.time()
        info = []
        for class_id, event in self.active_events.items():
            duration = current_time - event['start_time']
            info.append({
                'class_name': event['class_name'],
                'duration': duration,
                'detections': event['detection_count'],
                'confidence': event['max_confidence']
            })
        return info


class TelegramNotifier:
    """Sends notifications via Telegram."""
    
    def __init__(self, bot_token, chat_id, enabled=True):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bool(bot_token) and bool(chat_id)
        
        if not self.enabled:
            print("⚠️  Telegram notifications disabled")
        else:
            print(f"✓ Telegram notifications enabled (chat: {chat_id})")
    
    def send_alert(self, event, frame_path=None):
        """Send alert about confirmed event."""
        if not self.enabled:
            return False
        
        try:
            class_name = event['class_name']
            confidence = event['max_confidence']
            duration = event.get('duration', 0)
            detections = event.get('detection_count', 0)
            
            # Format message
            caption = (
                f"<b>🚨 ALERT: Fight Activity Detected</b>\n\n"
                f"👊 <b>Action:</b> {class_name}\n"
                f"📊 <b>Confidence:</b> {int(confidence * 100)}%\n"
                f"⏱ <b>Duration:</b> {duration:.1f}s\n"
                f"🔢 <b>Detections:</b> {detections}\n"
                f"🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Send photo if available
            if frame_path and os.path.exists(frame_path):
                url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
                with open(frame_path, 'rb') as f:
                    response = requests.post(url, data={
                        'chat_id': self.chat_id,
                        'caption': caption,
                        'parse_mode': 'HTML'
                    }, files={'photo': f}, timeout=15)
            else:
                # Send text only
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                response = requests.post(url, json={
                    'chat_id': self.chat_id,
                    'text': caption,
                    'parse_mode': 'HTML'
                }, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ Telegram alert sent: {class_name}")
                return True
            else:
                print(f"✗ Telegram error: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Telegram exception: {e}")
            return False


class FightMonitor:
    """Main monitoring system."""
    
    def __init__(self, model_path, camera_index=0, confidence=0.5):
        print("="*50)
        print("Fight Detection Monitoring System")
        print("="*50)
        
        # Load model
        print(f"\n📦 Loading model: {model_path}")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        self.model = YOLO(model_path)
        print("✓ Model loaded")
        
        # Initialize camera
        print(f"\n📷 Opening camera: {camera_index}")
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera: {camera_index}")
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"✓ Camera opened: {actual_width}x{actual_height}")
        
        self.confidence = confidence
        
        # Initialize components
        self.event_manager = EventManager(
            cooldown=EVENT_COOLDOWN,
            min_duration=EVENT_MIN_DURATION,
            min_detections=EVENT_MIN_DETECTIONS,
            timeout=EVENT_TIMEOUT
        )
        
        self.notifier = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID,
            enabled=TELEGRAM_ENABLED
        )
        
        # Create events directory
        if LOG_EVENTS:
            os.makedirs(EVENTS_DIR, exist_ok=True)
        
        # Stats
        self.frame_count = 0
        self.detection_count = 0
        self.alert_count = 0
        self.fps = 0
        self.fps_counter = 0
        self.fps_time = time.time()
        
        print(f"\n⚙️  Settings:")
        print(f"   Confidence: {confidence}")
        print(f"   Event cooldown: {EVENT_COOLDOWN}s")
        print(f"   Min duration: {EVENT_MIN_DURATION}s")
        print(f"   Min detections: {EVENT_MIN_DETECTIONS}")
        print("="*50)
        print("\nPress 'q' to quit\n")
    
    def process_frame(self, frame):
        """Process a single frame."""
        # Run inference
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            verbose=False,
            show=False
        )
        
        # Extract detections
        detections = []
        if results[0].boxes is not None:
            for box in results[0].boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].cpu().numpy().tolist()
                detections.append((class_id, confidence, bbox))
        
        # Get annotated frame
        annotated = results[0].plot(
            boxes=True,
            labels=True,
            conf=True,
            kpt_radius=5,
            kpt_line=True
        )
        
        return annotated, detections
    
    def save_event_frame(self, event):
        """Save event frame to disk."""
        if not LOG_EVENTS or event.get('best_frame') is None:
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        class_name = event['class_name']
        filename = f"{class_name}_{timestamp}.jpg"
        filepath = EVENTS_DIR / filename
        
        cv2.imwrite(str(filepath), event['best_frame'])
        return str(filepath)
    
    def draw_stats(self, frame):
        """Draw statistics overlay on frame."""
        h, w = frame.shape[:2]
        
        # Background for stats
        cv2.rectangle(frame, (10, 10), (300, 120), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (300, 120), (50, 50, 50), 1)
        
        # Stats text
        y = 35
        cv2.putText(frame, f"FPS: {self.fps}", (20, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        y += 25
        cv2.putText(frame, f"Detections: {self.detection_count}", (20, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        y += 25
        cv2.putText(frame, f"Alerts sent: {self.alert_count}", (20, y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 100), 2)
        y += 25
        
        # Active events
        active = self.event_manager.get_active_events_info()
        if active:
            cv2.putText(frame, f"Active: {len(active)} events", (20, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
        
        return frame
    
    def run(self):
        """Main monitoring loop."""
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to read frame")
                    time.sleep(0.1)
                    continue
                
                self.frame_count += 1
                
                # Process frame
                annotated, detections = self.process_frame(frame)
                self.detection_count += len(detections)
                
                # Process events
                confirmed_events = self.event_manager.process_detections(detections, annotated)
                
                # Handle confirmed events
                for event in confirmed_events:
                    print(f"\n🚨 EVENT CONFIRMED: {event['class_name']} "
                          f"(conf: {event['max_confidence']:.2f}, "
                          f"duration: {event['duration']:.1f}s, "
                          f"detections: {event['detection_count']})")
                    
                    # Save frame
                    frame_path = self.save_event_frame(event)
                    
                    # Send notification
                    if self.notifier.send_alert(event, frame_path):
                        self.alert_count += 1
                
                # Calculate FPS
                self.fps_counter += 1
                if time.time() - self.fps_time >= 1.0:
                    self.fps = self.fps_counter
                    self.fps_counter = 0
                    self.fps_time = time.time()
                
                # Draw stats
                if SHOW_STATS:
                    annotated = self.draw_stats(annotated)
                
                # Show frame
                cv2.imshow(WINDOW_NAME, annotated)
                
                # Handle key press
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Shutting down...")
                    break
                elif key == ord('s'):
                    # Save current frame
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    cv2.imwrite(f"screenshot_{timestamp}.jpg", annotated)
                    print(f"📸 Screenshot saved")
                    
        except KeyboardInterrupt:
            print("\n👋 Interrupted by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Release resources."""
        self.cap.release()
        cv2.destroyAllWindows()
        
        print("\n" + "="*50)
        print("Session Summary")
        print("="*50)
        print(f"Frames processed: {self.frame_count}")
        print(f"Total detections: {self.detection_count}")
        print(f"Alerts sent: {self.alert_count}")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(description="Fight Detection Monitoring System")
    parser.add_argument('--model', type=str, default=MODEL_PATH,
                       help=f'Path to model (default: {MODEL_PATH})')
    parser.add_argument('--camera', type=int, default=CAMERA_INDEX,
                       help=f'Camera index (default: {CAMERA_INDEX})')
    parser.add_argument('--conf', type=float, default=CONFIDENCE_THRESHOLD,
                       help=f'Confidence threshold (default: {CONFIDENCE_THRESHOLD})')
    parser.add_argument('--cooldown', type=int, default=EVENT_COOLDOWN,
                       help=f'Event cooldown in seconds (default: {EVENT_COOLDOWN})')
    parser.add_argument('--no-telegram', action='store_true',
                       help='Disable Telegram notifications')
    
    args = parser.parse_args()
    
    # Override config if needed
    if args.no_telegram:
        import config
        config.TELEGRAM_ENABLED = False
    
    if args.cooldown != EVENT_COOLDOWN:
        import config
        config.EVENT_COOLDOWN = args.cooldown
    
    try:
        monitor = FightMonitor(
            model_path=args.model,
            camera_index=args.camera,
            confidence=args.conf
        )
        monitor.run()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nCheck that the model exists at the specified path")
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        print("\nCheck that the camera is connected and not in use")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
