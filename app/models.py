from datetime import datetime
from app import db

class Camera(db.Model):
    """Camera/Video source model"""
    __tablename__ = 'cameras'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    source = db.Column(db.String(500), nullable=False)  # URL or camera index
    source_type = db.Column(db.String(20), default='webcam')  # webcam, rtsp, file
    is_active = db.Column(db.Boolean, default=True)
    location = db.Column(db.String(200))
    confidence_threshold = db.Column(db.Float, default=0.5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = db.relationship('DetectionEvent', back_populates='camera', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'source': self.source,
            'source_type': self.source_type,
            'is_active': self.is_active,
            'location': self.location,
            'confidence_threshold': self.confidence_threshold,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class DetectionEvent(db.Model):
    """Detection event model"""
    __tablename__ = 'detection_events'
    
    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'), nullable=False)
    event_type = db.Column(db.String(50), default='detection')
    detected_class = db.Column(db.String(100))  # Class name of detected object
    confidence = db.Column(db.Float, nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Float)  # seconds
    frame_path = db.Column(db.String(500))  # path to saved frame
    video_path = db.Column(db.String(500))  # path to saved video clip
    bbox_data = db.Column(db.Text)  # JSON string of bounding boxes
    keypoints_data = db.Column(db.Text)  # JSON string of keypoints
    status = db.Column(db.String(20), default='active')  # active, resolved, false_positive
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    camera = db.relationship('Camera', back_populates='events')
    
    def to_dict(self):
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'camera_name': self.camera.name if self.camera else None,
            'event_type': self.event_type,
            'detected_class': self.detected_class,
            'confidence': self.confidence,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'frame_path': self.frame_path,
            'video_path': self.video_path,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }


class SystemLog(db.Model):
    """System activity log model"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False)  # INFO, WARNING, ERROR
    message = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(100))
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'module': self.module,
            'camera_id': self.camera_id,
            'created_at': self.created_at.isoformat()
        }


class Settings(db.Model):
    """Application settings model"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(500))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat()
        }


