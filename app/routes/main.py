from flask import Blueprint, render_template, jsonify, request
from app.models import Camera, DetectionEvent, SystemLog, Settings
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func, desc

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@main_bp.route('/live')
def live():
    """Live monitoring page."""
    cameras = Camera.query.all()
    return render_template('live.html', cameras=cameras)


@main_bp.route('/camera/<int:camera_id>')
def camera_detail(camera_id):
    """Detailed camera view with real-time detection tracking."""
    camera = Camera.query.get_or_404(camera_id)
    
    # Get recent events for this camera
    recent_events = DetectionEvent.query.filter_by(camera_id=camera_id)\
        .order_by(DetectionEvent.created_at.desc())\
        .limit(10)\
        .all()
    
    return render_template('camera_detail.html', 
                         camera=camera, 
                         recent_events=recent_events)


@main_bp.route('/webcam')
def webcam():
    """Webcam launch page."""
    return render_template('webcam.html')


@main_bp.route('/history')
def history():
    """Event history page."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Filters
    camera_id = request.args.get('camera_id', type=int)
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build query
    query = DetectionEvent.query
    
    if camera_id:
        query = query.filter_by(camera_id=camera_id)
    if status:
        query = query.filter_by(status=status)
    if date_from:
        date_from_obj = datetime.fromisoformat(date_from)
        query = query.filter(DetectionEvent.start_time >= date_from_obj)
    if date_to:
        date_to_obj = datetime.fromisoformat(date_to)
        query = query.filter(DetectionEvent.start_time <= date_to_obj)
    
    # Order by most recent
    query = query.order_by(desc(DetectionEvent.start_time))
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    events = pagination.items
    
    cameras = Camera.query.all()
    
    return render_template(
        'history.html',
        events=events,
        cameras=cameras,
        pagination=pagination
    )


@main_bp.route('/settings')
def settings():
    """Settings page."""
    cameras = Camera.query.all()
    settings = Settings.query.all()
    return render_template('settings.html', cameras=cameras, settings=settings)


@main_bp.route('/statistics')
def statistics():
    """Statistics page."""
    # Get overall statistics
    total_cameras = Camera.query.count()
    active_cameras = Camera.query.filter_by(is_active=True).count()
    total_events = DetectionEvent.query.count()
    
    # Events in last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    events_24h = DetectionEvent.query.filter(
        DetectionEvent.start_time >= yesterday
    ).count()
    
    # Events in last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    events_7d = DetectionEvent.query.filter(
        DetectionEvent.start_time >= week_ago
    ).count()
    
    # Events by camera
    events_by_camera = db.session.query(
        Camera.name,
        func.count(DetectionEvent.id).label('count')
    ).join(DetectionEvent).group_by(Camera.id).all()
    
    # Events by hour (last 24 hours)
    events_by_hour = db.session.query(
        func.strftime('%H', DetectionEvent.start_time).label('hour'),
        func.count(DetectionEvent.id).label('count')
    ).filter(
        DetectionEvent.start_time >= yesterday
    ).group_by('hour').all()
    
    # Average confidence
    avg_confidence = db.session.query(
        func.avg(DetectionEvent.confidence)
    ).scalar() or 0
    
    # Average duration
    avg_duration = db.session.query(
        func.avg(DetectionEvent.duration)
    ).filter(
        DetectionEvent.duration.isnot(None)
    ).scalar() or 0
    
    return render_template(
        'statistics.html',
        total_cameras=total_cameras,
        active_cameras=active_cameras,
        total_events=total_events,
        events_24h=events_24h,
        events_7d=events_7d,
        events_by_camera=events_by_camera,
        events_by_hour=events_by_hour,
        avg_confidence=avg_confidence,
        avg_duration=avg_duration
    )


@main_bp.route('/logs')
def logs():
    """System logs page."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    level = request.args.get('level')
    
    query = SystemLog.query
    
    if level:
        query = query.filter_by(level=level)
    
    query = query.order_by(desc(SystemLog.created_at))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template(
        'logs.html',
        logs=pagination.items,
        pagination=pagination
    )


