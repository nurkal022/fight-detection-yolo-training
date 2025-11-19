from flask import Blueprint, Response, jsonify, current_app
from app.detection.detector import UniversalDetector
from app.models import Camera, DetectionEvent
from app import db, socketio
from app.utils.logger import log_system
from app.utils.telegram import TelegramNotifier
import cv2
import os
from datetime import datetime
import json

detection_bp = Blueprint('detection', __name__)

# Global detector instance
detector = None


def get_detector():
    """Get or create detector instance."""
    global detector
    if detector is None:
        model_path = current_app.config.get('MODEL_PATH', 'yolo11n.pt')
        confidence = current_app.config.get('CONFIDENCE_THRESHOLD', 0.5)
        cooldown = current_app.config.get('EVENT_COOLDOWN', 5)
        detection_classes = current_app.config.get('DETECTION_CLASSES', None)
        event_type = current_app.config.get('EVENT_TYPE', 'detection')
        
        detector = UniversalDetector(
            model_path=model_path,
            confidence_threshold=confidence,
            event_cooldown=cooldown,
            detection_classes=detection_classes,
            event_type=event_type
        )
        
        # Register callback for events
        detector.register_callback(handle_detection_event)
        
        log_system('INFO', f'Detector initialized with model: {model_path}', 'detection')
    
    return detector


def handle_detection_event(event_data):
    """
    Callback for handling detection events.
    Saves to database and emits to clients via WebSocket.
    """
    try:
        camera_id = event_data['camera_id']
        
        # Save frame if available
        frame_path = None
        if 'frame' in event_data:
            frame_dir = 'app/static/events'
            os.makedirs(frame_dir, exist_ok=True)
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            frame_filename = f'event_cam{camera_id}_{timestamp}.jpg'
            frame_path = os.path.join(frame_dir, frame_filename)
            
            cv2.imwrite(frame_path, event_data['frame'])
            frame_path = f'events/{frame_filename}'  # Relative path for web
        
        # Create database entry
        event = DetectionEvent(
            camera_id=camera_id,
            event_type=event_data.get('event_type', 'detection'),
            detected_class=event_data.get('detected_class', 'unknown'),
            confidence=event_data['confidence'],
            start_time=event_data['start_time'],
            end_time=event_data.get('end_time'),
            duration=event_data.get('duration'),
            frame_path=frame_path,
            status='active'
        )
        
        db.session.add(event)
        db.session.commit()
        
        log_system('INFO', f'Event logged: ID={event.id}, Camera={camera_id}, Class={event.detected_class}, Confidence={event.confidence:.2f}', 'detection')
        
        # Emit to connected clients via WebSocket
        socketio.emit('new_event', event.to_dict(), namespace='/')
        
        # Also emit alert
        socketio.emit('alert', {
            'type': event_data.get('event_type', 'detection'),
            'camera_id': camera_id,
            'detected_class': event.detected_class,
            'confidence': event.confidence,
            'timestamp': datetime.utcnow().isoformat()
        }, namespace='/')

        # Telegram notification (if enabled)
        try:
            notifier = TelegramNotifier()
            if notifier.is_ready():
                caption = (
                    f"<b>🚨 Detection Alert</b>\n"
                    f"Camera: {event.camera.name if event.camera else camera_id}\n"
                    f"Detected: {event.detected_class}\n"
                    f"Confidence: {int(event.confidence*100)}%\n"
                    f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                )
                sent = False
                if event.frame_path:
                    photo_fs_path = os.path.join('app/static', event.frame_path)
                    if os.path.exists(photo_fs_path):
                        sent = notifier.send_photo(photo_fs_path, caption)
                if not sent:
                    notifier.send_message(caption)
        except Exception as e:
            log_system('ERROR', f'Telegram notify error: {str(e)}', 'detection')
        
    except Exception as e:
        log_system('ERROR', f'Error handling detection event: {str(e)}', 'detection')


def generate_stream(camera_id):
    """
    Generate video stream for a camera.
    
    Args:
        camera_id: Camera ID to stream
        
    Yields:
        JPEG frames as multipart response
    """
    import time
    det = get_detector()
    
    log_system('INFO', f'Starting stream generation for camera {camera_id}', 'detection')
    frame_count = 0
    
    while True:
        frame = det.get_latest_frame(camera_id)
        
        if frame is None:
            # Wait a bit before retrying
            time.sleep(0.033)  # ~30 FPS
            continue
        
        frame_count += 1
        if frame_count % 100 == 0:
            log_system('INFO', f'Streamed {frame_count} frames for camera {camera_id}', 'detection')
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue
        
        frame_bytes = buffer.tobytes()
        
        # Yield as multipart response
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@detection_bp.route('/stream/<int:camera_id>')
def stream(camera_id):
    """
    Video stream endpoint.
    
    Args:
        camera_id: Camera ID to stream
    """
    return Response(
        generate_stream(camera_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@detection_bp.route('/start/<int:camera_id>', methods=['POST'])
def start_detection(camera_id):
    """
    Start detection for a camera.
    
    Args:
        camera_id: Camera ID to start
    """
    try:
        camera = Camera.query.get_or_404(camera_id)
        
        det = get_detector()
        success = det.start_stream(camera_id, camera.source, camera.source_type)
        
        if success:
            camera.is_active = True
            db.session.commit()
            
            log_system('INFO', f'Started detection for camera {camera.name}', 'detection', camera_id)
            
            return jsonify({
                'success': True,
                'message': f'Detection started for {camera.name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to start detection'
            }), 500
            
    except Exception as e:
        log_system('ERROR', f'Error starting detection: {str(e)}', 'detection', camera_id)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@detection_bp.route('/stop/<int:camera_id>', methods=['POST'])
def stop_detection(camera_id):
    """
    Stop detection for a camera.
    
    Args:
        camera_id: Camera ID to stop
    """
    try:
        camera = Camera.query.get_or_404(camera_id)
        
        det = get_detector()
        success = det.stop_stream(camera_id)
        
        if success:
            camera.is_active = False
            db.session.commit()
            
            log_system('INFO', f'Stopped detection for camera {camera.name}', 'detection', camera_id)
            
            return jsonify({
                'success': True,
                'message': f'Detection stopped for {camera.name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to stop detection'
            }), 500
            
    except Exception as e:
        log_system('ERROR', f'Error stopping detection: {str(e)}', 'detection', camera_id)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@detection_bp.route('/stats')
def get_stats():
    """Get detection statistics."""
    try:
        det = get_detector()
        stats = det.get_all_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@detection_bp.route('/status/<int:camera_id>')
def get_status(camera_id):
    """Get detection status for a camera."""
    try:
        det = get_detector()
        stats = det.get_stream_stats(camera_id)
        
        if stats:
            return jsonify({
                'success': True,
                'status': stats
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Camera not active'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


