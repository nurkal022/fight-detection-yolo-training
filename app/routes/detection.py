from flask import Blueprint, Response, jsonify, current_app
from app.detection.detector import UniversalDetector
from app.models import Camera, DetectionEvent
from app import db, socketio
from app.utils.logger import log_system
from app.utils.telegram import TelegramNotifier
import cv2
import os
import threading
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
        min_duration = current_app.config.get('EVENT_MIN_DURATION', 1)
        detection_classes = current_app.config.get('DETECTION_CLASSES', None)
        event_type = current_app.config.get('EVENT_TYPE', 'detection')
        
        detector = UniversalDetector(
            model_path=model_path,
            confidence_threshold=confidence,
            event_cooldown=cooldown,
            detection_classes=detection_classes,
            event_type=event_type,
            min_duration=min_duration
        )
        
        # Register callback for events
        detector.register_callback(handle_detection_event)
        
        log_system('INFO', f'Detector initialized with model: {model_path}, confidence={confidence}, cooldown={cooldown}s, min_duration={min_duration}s', 'detection')
    
    return detector


def handle_detection_event(event_data):
    """
    Callback for handling detection events.
    Saves to database and emits to clients via WebSocket.
    Implements false positive filtering.
    """
    try:
        camera_id = event_data['camera_id']
        confidence = event_data.get('confidence', 0.0)
        detection_count = event_data.get('detection_count', 0)
        duration = event_data.get('duration', 0.0)
        
        # False positive filtering
        min_confidence_for_alert = current_app.config.get('MIN_CONFIDENCE_FOR_ALERT', 0.7)
        min_detection_count = current_app.config.get('MIN_DETECTION_COUNT', 3)
        min_duration = current_app.config.get('EVENT_MIN_DURATION', 1)
        
        # Check if event meets minimum requirements
        should_alert = (
            confidence >= min_confidence_for_alert and
            detection_count >= min_detection_count and
            duration >= min_duration
        )
        
        if not should_alert:
            log_system('INFO', f'Event filtered (FP): Camera={camera_id}, Conf={confidence:.2f} (min={min_confidence_for_alert}), Count={detection_count} (min={min_detection_count}), Duration={duration:.1f}s (min={min_duration})', 'detection')
            return
        
        log_system('INFO', f'Event passed filter: Camera={camera_id}, Conf={confidence:.2f}, Count={detection_count}, Duration={duration:.1f}s', 'detection')
        
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
            confidence=confidence,
            start_time=event_data['start_time'],
            end_time=event_data.get('end_time'),
            duration=duration,
            frame_path=frame_path,
            status='active'
        )
        
        db.session.add(event)
        db.session.commit()
        
        log_system('INFO', f'Event logged: ID={event.id}, Camera={camera_id}, Class={event.detected_class}, Confidence={event.confidence:.2f}, Duration={duration:.1f}s, Detections={detection_count}', 'detection')
        
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

        # Telegram notification (if enabled and meets alert criteria) - ASYNC in separate thread
        # This prevents blocking the detection thread
        def send_telegram_notification():
        try:
            with current_app.app_context():  # Need app context for Flask config
            notifier = TelegramNotifier()
            if notifier.is_ready():
                camera_name = event.camera.name if event.camera else f"Camera {camera_id}"
                caption = (
                    f"<b>🚨 Fight Detection Alert</b>\n"
                    f"📹 Camera: {camera_name}\n"
                    f"👊 Detected: <b>{event.detected_class}</b>\n"
                    f"📊 Confidence: {int(event.confidence*100)}%\n"
                    f"⏱ Duration: {duration:.1f}s\n"
                    f"🔢 Detections: {detection_count}\n"
                    f"🕐 Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
                )
                sent = False
                if event.frame_path:
                    photo_fs_path = os.path.join('app/static', event.frame_path)
                    if os.path.exists(photo_fs_path):
                        # Send to multiple chat IDs if configured
                        chat_ids_str = current_app.config.get('TELEGRAM_CHAT_ID', '')
                        if ',' in chat_ids_str:
                            chat_ids = [cid.strip() for cid in chat_ids_str.split(',')]
                            results = notifier.send_photo_to_multiple(photo_fs_path, chat_ids, caption)
                            sent = results['success'] > 0
                            log_system('INFO', f'Telegram sent to {results["success"]}/{len(chat_ids)} chats', 'detection')
                        else:
                            sent = notifier.send_photo(photo_fs_path, caption)
                if not sent:
                    # Fallback to text message
                    chat_ids_str = current_app.config.get('TELEGRAM_CHAT_ID', '')
                    if ',' in chat_ids_str:
                        chat_ids = [cid.strip() for cid in chat_ids_str.split(',')]
                        results = notifier.send_message_to_multiple(caption, chat_ids)
                        log_system('INFO', f'Telegram text sent to {results["success"]}/{len(chat_ids)} chats', 'detection')
                    else:
                        notifier.send_message(caption)
        except Exception as e:
            log_system('ERROR', f'Telegram notify error: {str(e)}', 'detection')
        
        # Start Telegram notification in background thread (non-blocking)
        telegram_thread = threading.Thread(target=send_telegram_notification, daemon=True)
        telegram_thread.start()
        
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
    import numpy as np
    det = get_detector()
    
    log_system('INFO', f'Starting stream generation for camera {camera_id}', 'detection')
    frame_count = 0
    no_frame_count = 0
    target_fps = 30
    frame_time = 1.0 / target_fps  # ~33ms per frame
    
    while True:
        try:
            loop_start = time.time()
            
            # Get latest frame
            frame = det.get_latest_frame(camera_id)
            
            if frame is None:
                no_frame_count += 1
                # If no frame for too long, send black frame
                if no_frame_count > 30:  # ~1 second at 30 FPS
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        cv2.putText(frame, 'No signal', (200, 240), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                else:
                    time.sleep(frame_time)
                    continue
            else:
                no_frame_count = 0
            
            frame_count += 1
            if frame_count % 500 == 0:
                log_system('INFO', f'Streamed {frame_count} frames for camera {camera_id}', 'detection')
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                time.sleep(frame_time)
                continue
            
            frame_bytes = buffer.tobytes()
            
            # Yield as multipart response with Content-Length
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
                   b'\r\n' + frame_bytes + b'\r\n')
            
            # Maintain target FPS
            elapsed = time.time() - loop_start
            sleep_time = max(0, frame_time - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
        except Exception as e:
            log_system('ERROR', f'Error in stream generation for camera {camera_id}: {str(e)}', 'detection')
            time.sleep(0.05)
            continue


@detection_bp.route('/stream/<int:camera_id>')
def stream(camera_id):
    """
    Video stream endpoint.
    
    Args:
        camera_id: Camera ID to stream
    """
    return Response(
        generate_stream(camera_id),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate, private',
            'Pragma': 'no-cache',
            'Expires': '0',
            'X-Accel-Buffering': 'no'
        }
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


