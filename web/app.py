#!/usr/bin/env python3
"""
Fight Detection Web Application
Flask-based monitoring system with live detection and logging
"""

import os
import sys
import cv2
import time
import json
import logging
import threading
import requests
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Flask, render_template, Response, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from ultralytics import YOLO

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = BASE_DIR.parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fight-detection-secret-key')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{BASE_DIR}/app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Model
    MODEL_PATH = os.environ.get('MODEL_PATH', str(PROJECT_DIR / 'fight_pose_model_export' / 'best.pt'))
    CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', 0.5))
    DETECTION_CLASSES = [0, 1, 2, 3, 4, 5, 6, 7]  # Exclude neutral (8)
    
    # Camera
    CAMERA_INDEX = int(os.environ.get('CAMERA_INDEX', 0))
    
    # Event filtering
    EVENT_COOLDOWN = int(os.environ.get('EVENT_COOLDOWN', 30))
    EVENT_MIN_DURATION = float(os.environ.get('EVENT_MIN_DURATION', 5.0))
    EVENT_MIN_DETECTIONS = int(os.environ.get('EVENT_MIN_DETECTIONS', 3))
    EVENT_TIMEOUT = float(os.environ.get('EVENT_TIMEOUT', 3.0))
    
    # Telegram
    TELEGRAM_ENABLED = os.environ.get('TELEGRAM_ENABLED', 'True').lower() == 'true'
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8237778300:AAEfUDpqzZkzfvoPtT3ukKYODpD33sxlZv4')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1003207428650')

CLASS_NAMES = {
    0: 'bent_over', 1: 'covering_face', 2: 'face_slap', 3: 'fist_clenching',
    4: 'hair_clothes_drag', 5: 'head_down', 6: 'head_slap_back', 7: 'neck_grab',
    8: 'neutral_class'
}

# ============================================================================
# FLASK APP INITIALIZATION
# ============================================================================

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Logging setup
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
os.makedirs(BASE_DIR / 'static' / 'events', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(BASE_DIR / 'logs' / 'app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('fight_detection')

# ============================================================================
# DATABASE MODELS
# ============================================================================

class Event(db.Model):
    """Detection event model"""
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Float)
    detection_count = db.Column(db.Integer)
    frame_path = db.Column(db.String(200))
    telegram_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'class_name': self.class_name,
            'confidence': self.confidence,
            'duration': self.duration,
            'detection_count': self.detection_count,
            'frame_path': self.frame_path,
            'telegram_sent': self.telegram_sent,
            'created_at': self.created_at.isoformat()
        }

class Log(db.Model):
    """System log model"""
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'module': self.module,
            'created_at': self.created_at.isoformat()
        }

# Create tables
with app.app_context():
    db.create_all()

# ============================================================================
# LOGGING HELPER
# ============================================================================

def log(level, message, module='system'):
    """Log message to file, console, and database"""
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(f"[{module}] {message}")
    
    try:
        with app.app_context():
            entry = Log(level=level.upper(), message=message, module=module)
            db.session.add(entry)
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to save log to DB: {e}")
    
    # Emit to connected clients
    try:
        socketio.emit('log', {
            'level': level.upper(),
            'message': message,
            'module': module,
            'time': datetime.now().strftime('%H:%M:%S')
        })
    except:
        pass

# ============================================================================
# TELEGRAM NOTIFIER
# ============================================================================

class TelegramNotifier:
    def __init__(self):
        self.enabled = Config.TELEGRAM_ENABLED
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        
    def send(self, event_data, frame_path=None):
        if not self.enabled or not self.token or not self.chat_id:
            return False
        
        try:
            caption = (
                f"<b>🚨 Fight Detection Alert</b>\n\n"
                f"👊 <b>Action:</b> {event_data['class_name']}\n"
                f"📊 <b>Confidence:</b> {int(event_data['confidence'] * 100)}%\n"
                f"⏱ <b>Duration:</b> {event_data['duration']:.1f}s\n"
                f"🔢 <b>Detections:</b> {event_data['detection_count']}\n"
                f"🕐 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            if frame_path and os.path.exists(frame_path):
                url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
                with open(frame_path, 'rb') as f:
                    resp = requests.post(url, data={
                        'chat_id': self.chat_id,
                        'caption': caption,
                        'parse_mode': 'HTML'
                    }, files={'photo': f}, timeout=15)
            else:
                url = f"https://api.telegram.org/bot{self.token}/sendMessage"
                resp = requests.post(url, json={
                    'chat_id': self.chat_id,
                    'text': caption,
                    'parse_mode': 'HTML'
                }, timeout=10)
            
            return resp.status_code == 200
        except Exception as e:
            log('ERROR', f'Telegram error: {e}', 'telegram')
            return False

notifier = TelegramNotifier()

# ============================================================================
# DETECTOR
# ============================================================================

class Detector:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.model = None
        self.cap = None
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # Event tracking
        self.active_events = {}
        self.last_alert_time = {}
        
        # Stats
        self.fps = 0
        self.total_detections = 0
        self.total_alerts = 0
        
        self._initialized = True
    
    def load_model(self):
        if self.model is not None:
            return True
        
        model_path = Config.MODEL_PATH
        if not os.path.exists(model_path):
            log('ERROR', f'Model not found: {model_path}', 'detector')
            return False
        
        log('INFO', f'Loading model: {model_path}', 'detector')
        try:
            self.model = YOLO(model_path)
            log('INFO', 'Model loaded successfully', 'detector')
            return True
        except Exception as e:
            log('ERROR', f'Failed to load model: {e}', 'detector')
            return False
    
    def start_camera(self, camera_index=None):
        if camera_index is None:
            camera_index = Config.CAMERA_INDEX
        
        if self.cap is not None and self.cap.isOpened():
            log('INFO', 'Camera already opened', 'detector')
            return True
        
        log('INFO', f'Opening camera: {camera_index}', 'detector')
        
        try:
            self.cap = cv2.VideoCapture(camera_index)
            
            # Даем камере время на инициализацию
            time.sleep(0.5)
            
            if not self.cap.isOpened():
                log('ERROR', f'Failed to open camera: {camera_index}. Trying to check if camera exists...', 'detector')
                # Попробуем проверить другие индексы
                for i in range(3):
                    test_cap = cv2.VideoCapture(i)
                    if test_cap.isOpened():
                        ret, test_frame = test_cap.read()
                        test_cap.release()
                        if ret:
                            log('INFO', f'Found working camera at index {i}', 'detector')
                return False
            
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            # Проверяем, что можем читать кадры
            ret, test_frame = self.cap.read()
            if not ret or test_frame is None:
                log('ERROR', 'Camera opened but cannot read frames', 'detector')
                self.cap.release()
                self.cap = None
                return False
            
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            log('INFO', f'Camera opened successfully: {w}x{h}', 'detector')
            return True
        except Exception as e:
            log('ERROR', f'Exception opening camera: {e}', 'detector')
            if self.cap:
                self.cap.release()
                self.cap = None
            return False
    
    def stop_camera(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.running = False
        log('INFO', 'Camera stopped', 'detector')
    
    def start(self):
        if self.running:
            log('INFO', 'Detection already running', 'detector')
            return True
        
        log('INFO', 'Starting detection...', 'detector')
        
        if not self.load_model():
            log('ERROR', 'Failed to load model', 'detector')
            return False
        
        if not self.start_camera():
            log('ERROR', 'Failed to start camera', 'detector')
            return False
        
        self.running = True
        thread = threading.Thread(target=self._detection_loop, daemon=True)
        thread.start()
        log('INFO', 'Detection thread started', 'detector')
        return True
    
    def stop(self):
        self.running = False
        time.sleep(0.5)
        self.stop_camera()
        log('INFO', 'Detection stopped', 'detector')
    
    def _detection_loop(self):
        fps_counter = 0
        fps_time = time.time()
        frame_count = 0
        
        log('INFO', 'Detection loop started', 'detector')
        
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                log('WARNING', 'Camera not opened, waiting...', 'detector')
                time.sleep(1)
                continue
            
            ret, frame = self.cap.read()
            if not ret:
                log('WARNING', 'Failed to read frame', 'detector')
                time.sleep(0.1)
                continue
            
            frame_count += 1
            if frame_count == 1:
                log('INFO', f'First frame captured: {frame.shape}', 'detector')
            
            # Run detection
            try:
                if self.model is None:
                    log('ERROR', 'Model is None, cannot run detection', 'detector')
                    time.sleep(1)
                    continue
                
                results = self.model.predict(
                    source=frame,
                    conf=Config.CONFIDENCE_THRESHOLD,
                    verbose=False
                )
                
                # Extract detections
                detections = []
                if results[0].boxes is not None:
                    for box in results[0].boxes:
                        cls_id = int(box.cls[0])
                        if cls_id in Config.DETECTION_CLASSES:
                            conf = float(box.conf[0])
                            bbox = box.xyxy[0].cpu().numpy().tolist()
                            detections.append((cls_id, conf, bbox))
                            
                            # Emit detection event for Live Logs
                            try:
                                socketio.emit('detection', {
                                    'class_name': CLASS_NAMES.get(cls_id, f'class_{cls_id}'),
                                    'confidence': conf
                                })
                            except:
                                pass
                
                # Get annotated frame
                annotated = results[0].plot(
                    boxes=True, labels=True, conf=True,
                    kpt_radius=5, kpt_line=True
                )
                
                # Process events
                self._process_events(detections, annotated)
                
                # Update stats
                self.total_detections += len(detections)
                fps_counter += 1
                
                if time.time() - fps_time >= 1.0:
                    self.fps = fps_counter
                    fps_counter = 0
                    fps_time = time.time()
                
                # Draw stats
                self._draw_stats(annotated)
                
                # Update current frame
                try:
                    with self.frame_lock:
                        self.current_frame = annotated.copy()
                except Exception as e:
                    log('ERROR', f'Error updating frame: {e}', 'detector')
                
            except Exception as e:
                log('ERROR', f'Detection error: {e}', 'detector')
                import traceback
                log('ERROR', traceback.format_exc(), 'detector')
                time.sleep(0.1)
            
            time.sleep(0.001)
    
    def _process_events(self, detections, frame):
        current_time = time.time()
        detected_classes = set()
        
        # Group by class
        class_detections = defaultdict(list)
        for cls_id, conf, bbox in detections:
            class_detections[cls_id].append((conf, bbox))
            detected_classes.add(cls_id)
        
        # Update active events
        for cls_id, dets in class_detections.items():
            max_conf = max(d[0] for d in dets)
            
            if cls_id not in self.active_events:
                self.active_events[cls_id] = {
                    'class_id': cls_id,
                    'class_name': CLASS_NAMES.get(cls_id, f'class_{cls_id}'),
                    'start_time': current_time,
                    'last_detection': current_time,
                    'max_confidence': max_conf,
                    'detection_count': len(dets),
                    'best_frame': frame.copy()
                }
            else:
                event = self.active_events[cls_id]
                event['last_detection'] = current_time
                event['detection_count'] += len(dets)
                if max_conf > event['max_confidence']:
                    event['max_confidence'] = max_conf
                    event['best_frame'] = frame.copy()
        
        # Check for completed events
        to_remove = []
        for cls_id, event in self.active_events.items():
            time_since_last = current_time - event['last_detection']
            duration = current_time - event['start_time']
            
            if time_since_last >= Config.EVENT_TIMEOUT or cls_id not in detected_classes:
                # Event ended - check if should alert
                if (duration >= Config.EVENT_MIN_DURATION and 
                    event['detection_count'] >= Config.EVENT_MIN_DETECTIONS):
                    
                    last_alert = self.last_alert_time.get(cls_id, 0)
                    if current_time - last_alert >= Config.EVENT_COOLDOWN:
                        self._confirm_event(event, duration)
                        self.last_alert_time[cls_id] = current_time
                
                to_remove.append(cls_id)
        
        for cls_id in to_remove:
            del self.active_events[cls_id]
    
    def _confirm_event(self, event, duration):
        """Handle confirmed event"""
        event_data = {
            'class_name': event['class_name'],
            'confidence': event['max_confidence'],
            'duration': duration,
            'detection_count': event['detection_count']
        }
        
        log('WARNING', f"EVENT: {event['class_name']} (conf: {event['max_confidence']:.2f}, dur: {duration:.1f}s)", 'detector')
        
        # Save frame
        frame_path = None
        if event.get('best_frame') is not None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{event['class_name']}_{timestamp}.jpg"
            frame_path = str(BASE_DIR / 'static' / 'events' / filename)
            cv2.imwrite(frame_path, event['best_frame'])
            event_data['frame_path'] = f'events/{filename}'
        
        # Save to database
        try:
            with app.app_context():
                db_event = Event(
                    class_name=event_data['class_name'],
                    confidence=event_data['confidence'],
                    duration=event_data['duration'],
                    detection_count=event_data['detection_count'],
                    frame_path=event_data.get('frame_path')
                )
                db.session.add(db_event)
                db.session.commit()
                event_data['id'] = db_event.id
        except Exception as e:
            log('ERROR', f'Failed to save event: {e}', 'detector')
        
        # Send Telegram
        telegram_sent = notifier.send(event_data, frame_path)
        if telegram_sent:
            self.total_alerts += 1
            log('INFO', f'Telegram sent for {event["class_name"]}', 'telegram')
            
            # Update DB
            try:
                with app.app_context():
                    if 'id' in event_data:
                        db_event = Event.query.get(event_data['id'])
                        if db_event:
                            db_event.telegram_sent = True
                            db.session.commit()
            except:
                pass
        
        # Emit to clients
        socketio.emit('event', event_data)
    
    def _draw_stats(self, frame):
        h, w = frame.shape[:2]
        
        # Stats box
        cv2.rectangle(frame, (10, 10), (250, 100), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (250, 100), (50, 50, 50), 1)
        
        cv2.putText(frame, f'FPS: {self.fps}', (20, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f'Detections: {self.total_detections}', (20, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(frame, f'Alerts: {self.total_alerts}', (20, 85),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 100), 2)
        
        # Active events indicator
        if self.active_events:
            cv2.putText(frame, f'ACTIVE: {len(self.active_events)}', (w - 150, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    def get_frame(self):
        try:
            with self.frame_lock:
                if self.current_frame is not None:
                    return self.current_frame.copy()
        except Exception as e:
            log('ERROR', f'Error getting frame: {e}', 'detector')
        return None
    
    def get_stats(self):
        return {
            'running': self.running,
            'fps': self.fps,
            'total_detections': self.total_detections,
            'total_alerts': self.total_alerts,
            'active_events': len(self.active_events)
        }

# Global detector instance
detector = Detector()

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/live')
def live():
    return render_template('live.html')

@app.route('/events')
def events():
    events = Event.query.order_by(Event.created_at.desc()).limit(100).all()
    return render_template('events.html', events=events)

@app.route('/logs')
def logs():
    logs = Log.query.order_by(Log.created_at.desc()).limit(200).all()
    return render_template('logs.html', logs=logs)

@app.route('/statistics')
def statistics():
    return render_template('statistics.html')

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/start', methods=['POST'])
def api_start():
    log('INFO', '='*50, 'api')
    log('INFO', 'API: Start detection requested', 'api')
    log('INFO', f'Detector running: {detector.running}', 'api')
    log('INFO', f'Detector model loaded: {detector.model is not None}', 'api')
    log('INFO', f'Detector camera opened: {detector.cap is not None and (detector.cap.isOpened() if detector.cap else False)}', 'api')
    
    try:
        result = detector.start()
        log('INFO', f'Detector.start() returned: {result}', 'api')
        
        if result:
            log('INFO', 'API: Detection started successfully', 'api')
            log('INFO', f'After start - running: {detector.running}', 'api')
            return jsonify({'success': True, 'message': 'Detection started'})
        else:
            log('ERROR', 'API: Failed to start detection', 'api')
            return jsonify({'success': False, 'message': 'Failed to start detection. Check logs for details.'}), 500
    except Exception as e:
        log('ERROR', f'API: Exception starting detection: {e}', 'api')
        import traceback
        log('ERROR', traceback.format_exc(), 'api')
        return jsonify({'success': False, 'message': f'Exception: {str(e)}'}), 500

@app.route('/api/stop', methods=['POST'])
def api_stop():
    detector.stop()
    return jsonify({'success': True, 'message': 'Detection stopped'})

@app.route('/api/status')
def api_status():
    stats = detector.get_stats()
    # Добавляем дополнительную информацию для отладки
    stats['model_loaded'] = detector.model is not None
    stats['camera_opened'] = detector.cap is not None and (detector.cap.isOpened() if detector.cap else False)
    stats['has_frame'] = detector.current_frame is not None
    return jsonify(stats)

@app.route('/api/events')
def api_events():
    limit = request.args.get('limit', 50, type=int)
    events = Event.query.order_by(Event.created_at.desc()).limit(limit).all()
    return jsonify([e.to_dict() for e in events])

@app.route('/api/logs')
def api_logs():
    limit = request.args.get('limit', 100, type=int)
    level = request.args.get('level')
    
    query = Log.query
    if level:
        query = query.filter_by(level=level.upper())
    
    logs = query.order_by(Log.created_at.desc()).limit(limit).all()
    return jsonify([l.to_dict() for l in logs])

@app.route('/api/statistics/data')
def api_statistics_data():
    """Get statistics data for charts with test data"""
    import random
    
    # Real data from database
    with app.app_context():
        total_events = Event.query.count()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        
        # Events by class
        events_by_class = {}
        for event in Event.query.filter(Event.created_at >= week_ago).all():
            events_by_class[event.class_name] = events_by_class.get(event.class_name, 0) + 1
        
        # Events by hour (last 24 hours)
        events_by_hour = [0] * 24
        yesterday = datetime.utcnow() - timedelta(days=1)
        for event in Event.query.filter(Event.created_at >= yesterday).all():
            hour = event.created_at.hour
            events_by_hour[hour] = events_by_hour[hour] + 1
        
        # Events by day (last 7 days)
        events_by_day = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            count = Event.query.filter(
                Event.created_at >= day,
                Event.created_at < day + timedelta(days=1)
            ).count()
            events_by_day.append({
                'date': day.strftime('%d.%m'),
                'count': count
            })
    
    # Add test data if not enough real data
    if total_events < 10:
        # Test data for classes
        test_classes = ['bent_over', 'fist_clenching', 'face_slap', 'neck_grab', 
                       'covering_face', 'head_slap_back', 'hair_clothes_drag', 'head_down']
        for cls in test_classes:
            if cls not in events_by_class:
                events_by_class[cls] = random.randint(5, 25)
        
        # Test data for hours
        if sum(events_by_hour) < 10:
            events_by_hour = [random.randint(0, 8) for _ in range(24)]
        
        # Test data for days
        if sum(d['count'] for d in events_by_day) < 10:
            events_by_day = [
                {'date': (today - timedelta(days=i)).strftime('%d.%m'), 
                 'count': random.randint(3, 15)}
                for i in range(6, -1, -1)
            ]
    
    # Format for charts
    class_names_ru = {
        'bent_over': 'Наклон вперед',
        'covering_face': 'Закрытие лица',
        'face_slap': 'Удар по лицу',
        'fist_clenching': 'Сжатие кулака',
        'hair_clothes_drag': 'Таскание за волосы',
        'head_down': 'Опущенная голова',
        'head_slap_back': 'Удар по затылку',
        'neck_grab': 'Захват за шею'
    }
    
    classes_data = []
    classes_labels = []
    for cls, count in sorted(events_by_class.items(), key=lambda x: x[1], reverse=True):
        classes_labels.append(class_names_ru.get(cls, cls))
        classes_data.append(count)
    
    return jsonify({
        'events_by_class': {
            'labels': classes_labels,
            'data': classes_data
        },
        'events_by_hour': {
            'labels': [f'{h:02d}:00' for h in range(24)],
            'data': events_by_hour
        },
        'events_by_day': {
            'labels': [d['date'] for d in events_by_day],
            'data': [d['count'] for d in events_by_day]
        },
        'total_events': total_events,
        'today_events': Event.query.filter(Event.created_at >= today).count() if total_events > 0 else random.randint(5, 15),
        'week_events': Event.query.filter(Event.created_at >= week_ago).count() if total_events > 0 else random.randint(30, 80)
    })

@app.route('/api/stats')
def api_stats():
    with app.app_context():
        total_events = Event.query.count()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_events = Event.query.filter(Event.created_at >= today).count()
        telegram_sent = Event.query.filter_by(telegram_sent=True).count()
        
    return jsonify({
        'detector': detector.get_stats(),
        'total_events': total_events,
        'today_events': today_events,
        'telegram_sent': telegram_sent
    })

@app.route('/api/active-events')
def api_active_events():
    """Get detailed active events"""
    events = []
    current_time = time.time()
    
    for cls_id, event in detector.active_events.items():
        duration = current_time - event['start_time']
        events.append({
            'class_name': event['class_name'],
            'max_confidence': event['max_confidence'],
            'duration': duration,
            'detection_count': event['detection_count']
        })
    
    return jsonify({'success': True, 'events': events})

@app.route('/api/diagnostics/camera')
def api_diagnostics_camera():
    """Check camera availability"""
    camera_index = Config.CAMERA_INDEX
    result = {
        'camera_index': camera_index,
        'available': False,
        'can_read': False,
        'resolution': None,
        'error': None
    }
    
    try:
        test_cap = cv2.VideoCapture(camera_index)
        time.sleep(0.3)
        
        if test_cap.isOpened():
            result['available'] = True
            ret, frame = test_cap.read()
            
            if ret and frame is not None:
                result['can_read'] = True
                result['resolution'] = {
                    'width': int(test_cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'height': int(test_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                }
            else:
                result['error'] = 'Camera opened but cannot read frames'
        else:
            result['error'] = f'Cannot open camera {camera_index}'
        
        test_cap.release()
    except Exception as e:
        result['error'] = str(e)
    
    return jsonify(result)

# ============================================================================
# VIDEO STREAM
# ============================================================================

def generate_frames():
    """Generate video frames for streaming"""
    frame_count = 0
    while True:
        frame = detector.get_frame()
        
        if frame is None:
            # Generate placeholder
            placeholder = create_placeholder_frame()
            ret, buffer = cv2.imencode('.jpg', placeholder)
            if frame_count == 0:
                log('INFO', 'Video stream: No frame available, showing placeholder', 'stream')
        else:
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if frame_count == 0:
                log('INFO', f'Video stream: First frame sent: {frame.shape}', 'stream')
        
        frame_count += 1
        
        if ret:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        time.sleep(0.033)  # ~30 FPS

def create_placeholder_frame():
    """Create placeholder frame when camera not active"""
    frame = 50 * (1 + 0 * cv2.imread.__doc__.__len__())  # Just get 50
    placeholder = frame * (1 + 0) * (1 + 0) + 0
    img = (placeholder // 50) * 50 + 0
    # Actually create the frame
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (30, 30, 30)
    
    cv2.putText(frame, 'Camera Not Active', (180, 220),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
    cv2.putText(frame, 'Click "Start Detection" to begin', (140, 260),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 1)
    
    return frame

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

# ============================================================================
# SOCKETIO EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    log('INFO', 'Client connected', 'websocket')

@socketio.on('disconnect')
def handle_disconnect():
    log('INFO', 'Client disconnected', 'websocket')

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    log('INFO', '='*50, 'system')
    log('INFO', 'Fight Detection Web Application', 'system')
    log('INFO', '='*50, 'system')
    log('INFO', f'Model: {Config.MODEL_PATH}', 'system')
    log('INFO', f'Telegram: {"Enabled" if Config.TELEGRAM_ENABLED else "Disabled"}', 'system')
    log('INFO', f'Confidence: {Config.CONFIDENCE_THRESHOLD}', 'system')
    log('INFO', f'Event cooldown: {Config.EVENT_COOLDOWN}s', 'system')
    log('INFO', f'Min duration: {Config.EVENT_MIN_DURATION}s', 'system')
    log('INFO', '='*50, 'system')
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)
