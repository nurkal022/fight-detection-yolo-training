from flask import Blueprint, jsonify, request, current_app
from app.models import Camera, DetectionEvent, SystemLog, Settings
from app import db
from app.utils.logger import log_system
from app.utils.telegram import TelegramNotifier
from datetime import datetime
from sqlalchemy import desc
import os
import cv2
import random
import tempfile

api_bp = Blueprint('api', __name__)


# ========== Camera Management ==========

@api_bp.route('/cameras', methods=['GET'])
def get_cameras():
    """Get all cameras."""
    cameras = Camera.query.all()
    return jsonify({
        'success': True,
        'cameras': [camera.to_dict() for camera in cameras]
    })


@api_bp.route('/cameras/<int:camera_id>', methods=['GET'])
def get_camera(camera_id):
    """Get a specific camera."""
    camera = Camera.query.get_or_404(camera_id)
    return jsonify({
        'success': True,
        'camera': camera.to_dict()
    })


@api_bp.route('/cameras', methods=['POST'])
def create_camera():
    """Create a new camera."""
    try:
        data = request.get_json()
        
        camera = Camera(
            name=data['name'],
            source=data['source'],
            source_type=data.get('source_type', 'webcam'),
            location=data.get('location'),
            confidence_threshold=data.get('confidence_threshold', 0.5),
            is_active=False
        )
        
        db.session.add(camera)
        db.session.commit()
        
        log_system('INFO', f'Camera created: {camera.name}', 'api')
        
        return jsonify({
            'success': True,
            'message': 'Camera created successfully',
            'camera': camera.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        log_system('ERROR', f'Error creating camera: {str(e)}', 'api')
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@api_bp.route('/cameras/<int:camera_id>', methods=['PUT'])
def update_camera(camera_id):
    """Update a camera."""
    try:
        camera = Camera.query.get_or_404(camera_id)
        data = request.get_json()
        
        if 'name' in data:
            camera.name = data['name']
        if 'source' in data:
            camera.source = data['source']
        if 'source_type' in data:
            camera.source_type = data['source_type']
        if 'location' in data:
            camera.location = data['location']
        if 'confidence_threshold' in data:
            camera.confidence_threshold = data['confidence_threshold']
        if 'is_active' in data:
            camera.is_active = data['is_active']
        
        db.session.commit()
        
        log_system('INFO', f'Camera updated: {camera.name}', 'api', camera_id)
        
        return jsonify({
            'success': True,
            'message': 'Camera updated successfully',
            'camera': camera.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        log_system('ERROR', f'Error updating camera: {str(e)}', 'api', camera_id)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@api_bp.route('/cameras/<int:camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    """Delete a camera."""
    try:
        camera = Camera.query.get_or_404(camera_id)
        camera_name = camera.name
        
        db.session.delete(camera)
        db.session.commit()
        
        log_system('INFO', f'Camera deleted: {camera_name}', 'api')
        
        return jsonify({
            'success': True,
            'message': 'Camera deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        log_system('ERROR', f'Error deleting camera: {str(e)}', 'api', camera_id)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========== Events Management ==========

@api_bp.route('/events', methods=['GET'])
def get_events():
    """Get all events with optional filters."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    camera_id = request.args.get('camera_id', type=int)
    status = request.args.get('status')
    
    query = DetectionEvent.query
    
    if camera_id:
        query = query.filter_by(camera_id=camera_id)
    if status:
        query = query.filter_by(status=status)
    
    query = query.order_by(desc(DetectionEvent.start_time))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'success': True,
        'events': [event.to_dict() for event in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page
    })


@api_bp.route('/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get a specific event."""
    event = DetectionEvent.query.get_or_404(event_id)
    return jsonify({
        'success': True,
        'event': event.to_dict()
    })


@api_bp.route('/events/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    """Update an event (e.g., mark as resolved)."""
    try:
        event = DetectionEvent.query.get_or_404(event_id)
        data = request.get_json()
        
        if 'status' in data:
            event.status = data['status']
        if 'notes' in data:
            event.notes = data['notes']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Event updated successfully',
            'event': event.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@api_bp.route('/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Delete an event."""
    try:
        event = DetectionEvent.query.get_or_404(event_id)
        
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Event deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========== Statistics ==========

@api_bp.route('/statistics/summary', methods=['GET'])
def get_statistics_summary():
    """Get overall statistics summary."""
    from datetime import timedelta
    from sqlalchemy import func
    
    total_cameras = Camera.query.count()
    active_cameras = Camera.query.filter_by(is_active=True).count()
    total_events = DetectionEvent.query.count()
    
    yesterday = datetime.utcnow() - timedelta(days=1)
    events_24h = DetectionEvent.query.filter(
        DetectionEvent.start_time >= yesterday
    ).count()
    
    return jsonify({
        'success': True,
        'statistics': {
            'total_cameras': total_cameras,
            'active_cameras': active_cameras,
            'total_events': total_events,
            'events_24h': events_24h
        }
    })


# ========== Settings ==========

@api_bp.route('/settings', methods=['GET'])
def get_settings():
    """Get all settings."""
    settings = Settings.query.all()
    return jsonify({
        'success': True,
        'settings': [setting.to_dict() for setting in settings]
    })


@api_bp.route('/settings/<key>', methods=['GET'])
def get_setting(key):
    """Get a specific setting."""
    setting = Settings.query.filter_by(key=key).first_or_404()
    return jsonify({
        'success': True,
        'setting': setting.to_dict()
    })


@api_bp.route('/settings', methods=['POST'])
def create_setting():
    """Create or update a setting."""
    try:
        data = request.get_json()
        
        setting = Settings.query.filter_by(key=data['key']).first()
        
        if setting:
            setting.value = data['value']
            if 'description' in data:
                setting.description = data['description']
        else:
            setting = Settings(
                key=data['key'],
                value=data['value'],
                description=data.get('description')
            )
            db.session.add(setting)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Setting saved successfully',
            'setting': setting.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ========== Logs ==========

@api_bp.route('/logs', methods=['GET'])
def get_logs():
    """Get system logs."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    level = request.args.get('level')
    
    query = SystemLog.query
    
    if level:
        query = query.filter_by(level=level)
    
    query = query.order_by(desc(SystemLog.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'success': True,
        'logs': [log.to_dict() for log in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page
    })


# ========== Health Check ==========

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })


# ========== Notifications ==========

@api_bp.route('/notifications/test-telegram', methods=['POST'])
def send_test_telegram():
    """Send a test Telegram message."""
    try:
        data = request.get_json(silent=True) or {}
        
        caption = data.get('caption') or (
            f"🚨 TEST DETECTION! 🚨\n"
            f"System detection test\n\n"
            f"📹 Camera: Test Camera\n"
            f"🎯 Confidence: 0.95\n"
            f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
            f"✅ System is working correctly!"
        )

        notifier = TelegramNotifier()
        if not notifier.enabled:
            return jsonify({
                'success': False,
                'message': 'Telegram notifications are disabled'
            }), 400

        if not notifier.bot_token:
            return jsonify({
                'success': False,
                'message': 'Telegram bot token is not configured'
            }), 400

        if not notifier.chat_id:
            return jsonify({
                'success': False,
                'message': 'Telegram chat ID is not configured'
            }), 400

        sent = notifier.send_message(caption)

        if sent:
            log_system('INFO', 'Test Telegram notification sent', 'api')
            return jsonify({'success': True, 'message': 'Test Telegram notification sent'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send Telegram notification'}), 500
    except Exception as e:
        log_system('ERROR', f'Test Telegram notify error: {str(e)}', 'api')
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/notifications/test-detection', methods=['POST'])
def send_test_detection():
    """Send test detection message with real detection from dataset image to all users."""
    try:
        data = request.get_json(silent=True) or {}
        
        # Get detector
        from app.routes.detection import get_detector
        detector = get_detector()
        
        # Check if specific image paths provided
        image_paths = data.get('image_paths', [])
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if image_paths:
            # Use provided image paths
            selected_images = []
            for img_path in image_paths:
                # Support both absolute and relative paths
                if os.path.isabs(img_path):
                    full_path = img_path
                else:
                    # Try relative to project root
                    full_path = os.path.join(os.path.dirname(base_dir), img_path)
                    if not os.path.exists(full_path):
                        # Try relative to other_version
                        full_path = os.path.join(base_dir, img_path)
                
                if os.path.exists(full_path):
                    selected_images.append({
                        'path': full_path,
                        'class': 'custom',
                        'filename': os.path.basename(full_path)
                    })
            
            if not selected_images:
                return jsonify({
                    'success': False,
                    'message': 'None of the provided image paths exist'
                }), 404
            
            # Use first image or random if multiple
            selected_image = selected_images[0] if len(selected_images) == 1 else random.choice(selected_images)
            image_path = selected_image['path']
        else:
            # Get dataset directory
            dataset_dir = os.path.join(base_dir, 'dataset')
            
            if not os.path.exists(dataset_dir):
                return jsonify({
                    'success': False,
                    'message': 'Dataset directory not found'
                }), 404
            
            # Find all images in dataset
            all_images = []
            for class_name in os.listdir(dataset_dir):
                class_path = os.path.join(dataset_dir, class_name)
                if os.path.isdir(class_path):
                    for filename in os.listdir(class_path):
                        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                            all_images.append({
                                'path': os.path.join(class_path, filename),
                                'class': class_name,
                                'filename': filename
                            })
            
            if not all_images:
                return jsonify({
                    'success': False,
                    'message': 'No images found in dataset'
                }), 404
            
            # Pick random image
            selected_image = random.choice(all_images)
            image_path = selected_image['path']
        
        # Check if image exists
        if not os.path.exists(image_path):
            return jsonify({
                'success': False,
                'message': f'Image not found: {image_path}'
            }), 404
        
        # Read image for detection (but send original without annotation)
        img = cv2.imread(image_path)
        if img is None:
            return jsonify({
                'success': False,
                'message': f'Failed to read image: {image_path}'
            }), 400
        
        # Run detection to get info (but don't annotate the image)
        annotated_frame, detections, has_detection = detector.detect_frame(img)
        
        # Prepare detection info
        detection_info = []
        max_confidence = 0.0
        detected_classes = set()
        
        for det in detections:
            class_name_det = det.get('class_name', f"class_{det['class']}")
            confidence = det['confidence']
            detected_classes.add(class_name_det)
            if confidence > max_confidence:
                max_confidence = confidence
            detection_info.append(f"{class_name_det}: {confidence:.2%}")
        
        # Get chat IDs to send to
        chat_ids = data.get('chat_ids', [])
        
        # If no chat_ids provided, use default from config or get from Settings
        if not chat_ids:
            default_chat_id = current_app.config.get('TELEGRAM_CHAT_ID', '')
            if default_chat_id:
                # Support comma-separated chat IDs
                chat_ids = [cid.strip() for cid in default_chat_id.split(',') if cid.strip()]
            else:
                # Try to get from Settings
                telegram_setting = Settings.query.filter_by(key='telegram_chat_ids').first()
                if telegram_setting and telegram_setting.value:
                    # Assume comma-separated list
                    chat_ids = [cid.strip() for cid in telegram_setting.value.split(',') if cid.strip()]
        
        if not chat_ids:
            return jsonify({
                'success': False,
                'message': 'No chat IDs configured. Provide chat_ids in request or set TELEGRAM_CHAT_ID in config.'
            }), 400
        
        # Extract class name from filename or path
        filename = selected_image['filename']
        class_name = selected_image.get('class', 'custom')
        
        # Try to extract class from filename (e.g., "lean_forward_to_victim_..." -> "lean forward to victim")
        if class_name == 'custom' and '_' in filename:
            # Try to extract meaningful class name from filename
            # Remove extension and common prefixes
            name_without_ext = os.path.splitext(filename)[0]
            # If filename contains class info (like dataset format)
            parts = name_without_ext.split('_')
            if len(parts) > 3:
                # Likely dataset format: class_timestamp_cam...
                potential_class = '_'.join(parts[:-3])  # Take first parts as class
                # Replace underscores with spaces and capitalize
                class_name = potential_class.replace('_', ' ').title()
            else:
                class_name = name_without_ext.replace('_', ' ').title()
        
        # Also check if class info provided in request
        if data.get('class_name'):
            class_name = data.get('class_name')
        
        # Prepare detailed caption with detection info
        if has_detection:
            detected_classes_str = ', '.join(sorted(detected_classes))
            caption = (
                f"<b>Класс:</b> {class_name}\n\n"
                f"<b>Файл:</b> {filename}\n\n"
                f"🎯 <b>Обнаружено:</b>\n"
                f"   Классы: {detected_classes_str}\n"
                f"   Уверенность: {max_confidence:.1%}\n"
                f"   Количество: {len(detections)}\n\n"
            )
            if detection_info:
                caption += f"📊 <b>Детали:</b>\n"
                for info in detection_info:
                    caption += f"   • {info}\n"
            caption += f"\n⏰ <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            caption = (
                f"<b>Класс:</b> {class_name}\n\n"
                f"<b>Файл:</b> {filename}\n\n"
                f"❌ Детекции не обнаружено\n\n"
                f"⏰ <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        # Send original image without detection/annotation (but with detailed text)
        notifier = TelegramNotifier()
        results = notifier.send_photo_to_multiple(image_path, chat_ids, caption)
        
        log_system('INFO', f'Image sent to {results["success"]} users, failed: {results["failed"]}', 'api')
        
        return jsonify({
            'success': True,
            'message': f'Image sent to {results["success"]} users',
            'results': {
                'sent': results['success'],
                'failed': results['failed'],
                'errors': results['errors']
            },
            'image_source': {
                'class': selected_image['class'],
                'filename': selected_image['filename'],
                'path': image_path
            }
        })
        
    except Exception as e:
        log_system('ERROR', f'Test detection error: {str(e)}', 'api')
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


