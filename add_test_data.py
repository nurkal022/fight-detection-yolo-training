#!/usr/bin/env python3
"""
Script to add test/demo data to the detection system
Creates fake cameras and sample detection events for demonstration
"""
import sys
import os
from datetime import datetime, timedelta, timezone
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Camera, DetectionEvent, SystemLog

# Test camera configurations
TEST_CAMERAS = [
    {
        'name': 'Главный вход - Вестибюль',
        'source': '0',  # Webcam index
        'source_type': 'webcam',
        'location': 'Вестибюль, 1 этаж',
        'confidence_threshold': 0.65,
        'is_active': False
    },
    {
        'name': 'Камера 2 - Коридор',
        'source': '1',
        'source_type': 'webcam',
        'location': 'Коридор, 2 этаж',
        'confidence_threshold': 0.6,
        'is_active': False
    },
    {
        'name': 'Демо RTSP камера',
        'source': 'rtsp://demo:demo@ipvmdemo.dyndns.org:5541/onvif-media/media.amp?profile=profile_1_h264&sessiontimeout=60&streamtimeout=60',
        'source_type': 'rtsp',
        'location': 'Демо локация',
        'confidence_threshold': 0.7,
        'is_active': False
    },
    {
        'name': 'Тестовая камера - Офис',
        'source': '2',
        'source_type': 'webcam',
        'location': 'Офис, 3 этаж',
        'confidence_threshold': 0.55,
        'is_active': False
    },
    {
        'name': 'Фейк камера - Склад',
        'source': '3',
        'source_type': 'webcam',
        'location': 'Склад, подвал',
        'confidence_threshold': 0.65,
        'is_active': False
    },
    {
        'name': 'Демо файл камера',
        'source': 'test_video.mp4',  # Placeholder - user can add actual video file
        'source_type': 'file',
        'location': 'Тестовая локация',
        'confidence_threshold': 0.6,
        'is_active': False
    }
]

# Detection classes for test events
DETECTION_CLASSES = [
    'covering_face',
    'neck_grab',
    'face_slap',
    'hair_clothes_drag',
    'fist_clenching',
    'head_slap_back',
    'bent_over',
    'head_down'
]


def create_test_cameras():
    """Create test cameras"""
    print("📹 Creating test cameras...")
    
    created_count = 0
    skipped_count = 0
    
    for camera_data in TEST_CAMERAS:
        # Check if camera already exists
        existing = Camera.query.filter_by(
            name=camera_data['name']
        ).first()
        
        if existing:
            print(f"  ⏭️  Skipping '{camera_data['name']}' - already exists")
            skipped_count += 1
            continue
        
        camera = Camera(**camera_data)
        db.session.add(camera)
        created_count += 1
        print(f"  ✓ Created: {camera_data['name']} ({camera_data['source_type']})")
    
    db.session.commit()
    print(f"\n✅ Created {created_count} cameras, skipped {skipped_count}")
    return created_count


def create_test_events():
    """Create sample detection events for demonstration"""
    print("\n🔴 Creating test detection events...")
    
    cameras = Camera.query.all()
    if not cameras:
        print("  ⚠️  No cameras found. Create cameras first.")
        return 0
    
    created_count = 0
    
    # Create events for each camera
    for camera in cameras:
        # Create 2-5 events per camera
        num_events = random.randint(2, 5)
        
        for i in range(num_events):
            # Random time in the last 7 days
            days_ago = random.randint(0, 7)
            hours_ago = random.randint(0, 23)
            start_time = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)
            
            # Random duration between 2-15 seconds
            duration = random.uniform(2.0, 15.0)
            end_time = start_time + timedelta(seconds=duration)
            
            # Random detection class and confidence
            detected_class = random.choice(DETECTION_CLASSES)
            confidence = random.uniform(0.65, 0.95)
            
            # Random status
            status = random.choice(['active', 'resolved', 'false_positive'])
            
            event = DetectionEvent(
                camera_id=camera.id,
                event_type='fight_detection',
                detected_class=detected_class,
                confidence=confidence,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                status=status,
                notes=f'Тестовое событие #{i+1} для демонстрации'
            )
            
            db.session.add(event)
            created_count += 1
    
    db.session.commit()
    print(f"✅ Created {created_count} test events")
    return created_count


def create_test_logs():
    """Create sample system logs"""
    print("\n📝 Creating test system logs...")
    
    cameras = Camera.query.all()
    created_count = 0
    
    log_messages = [
        ('INFO', 'Система запущена', 'system'),
        ('INFO', 'Детектор инициализирован', 'detector'),
        ('INFO', 'Модель YOLO загружена', 'detector'),
        ('WARNING', 'Камера временно недоступна', 'detection'),
        ('INFO', 'Детекция начата', 'detection'),
        ('INFO', 'Событие зарегистрировано', 'detection'),
        ('ERROR', 'Ошибка подключения к камере', 'detection'),
        ('INFO', 'Telegram уведомление отправлено', 'notifier'),
    ]
    
    for i in range(20):
        level, message, module = random.choice(log_messages)
        camera_id = random.choice(cameras).id if cameras else None
        
        # Random time in the last 3 days
        days_ago = random.randint(0, 3)
        hours_ago = random.randint(0, 23)
        created_at = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)
        
        log = SystemLog(
            level=level,
            message=message,
            module=module,
            camera_id=camera_id,
            created_at=created_at
        )
        
        db.session.add(log)
        created_count += 1
    
    db.session.commit()
    print(f"✅ Created {created_count} test logs")
    return created_count


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Add test/demo data to detection system')
    parser.add_argument('--cameras-only', action='store_true', help='Create only cameras')
    parser.add_argument('--events-only', action='store_true', help='Create only events')
    parser.add_argument('--logs-only', action='store_true', help='Create only logs')
    parser.add_argument('--no-events', action='store_true', help='Skip events creation')
    parser.add_argument('--no-logs', action='store_true', help='Skip logs creation')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧪 Adding Test/Demo Data to Detection System")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            cameras_created = 0
            events_created = 0
            logs_created = 0
            
            # Create cameras
            if not (args.events_only or args.logs_only):
                cameras_created = create_test_cameras()
            
            # Create events
            if not (args.cameras_only or args.logs_only or args.no_events):
                events_created = create_test_events()
            
            # Create logs
            if not (args.cameras_only or args.events_only or args.no_logs):
                logs_created = create_test_logs()
            
            print("\n" + "=" * 60)
            print("✅ Test data added successfully!")
            if cameras_created > 0:
                print(f"   📹 Cameras: {cameras_created} created")
            if events_created > 0:
                print(f"   🔴 Events: {events_created} created")
            if logs_created > 0:
                print(f"   📝 Logs: {logs_created} created")
            print("=" * 60)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()

