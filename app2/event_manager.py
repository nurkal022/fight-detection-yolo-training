"""
Simple event manager for tracking detections
"""
import time
from datetime import datetime


class EventManager:
    """Manages detection events and cooldowns"""
    
    def __init__(self, cooldown_seconds=30, min_duration=2):
        """
        Initialize event manager.
        
        Args:
            cooldown_seconds: Seconds between duplicate events
            min_duration: Minimum duration in seconds to consider event valid
        """
        self.cooldown_seconds = cooldown_seconds
        self.min_duration = min_duration
        self.active_events = {}  # camera_id -> event_data
        self.last_event_time = {}  # camera_id -> timestamp
        
    def start_event(self, camera_id, detected_class, confidence):
        """Start a new detection event"""
        current_time = time.time()
        
        # Check cooldown
        if camera_id in self.last_event_time:
            time_since_last = current_time - self.last_event_time[camera_id]
            if time_since_last < self.cooldown_seconds:
                return None
        
        # Start new event
        event_data = {
            'camera_id': camera_id,
            'detected_class': detected_class,
            'confidence': confidence,
            'max_confidence': confidence,
            'start_time': datetime.utcnow(),
            'detection_count': 1,
        }
        
        self.active_events[camera_id] = event_data
        return event_data
        
    def update_event(self, camera_id, confidence, detected_class=None):
        """Update active event"""
        if camera_id not in self.active_events:
            return None
            
        event = self.active_events[camera_id]
        event['detection_count'] += 1
        if confidence > event['max_confidence']:
            event['max_confidence'] = confidence
        if detected_class:
            event['detected_class'] = detected_class
            
        return event
        
    def end_event(self, camera_id):
        """End active event and return event data"""
        if camera_id not in self.active_events:
            return None
            
        event = self.active_events[camera_id]
        event['end_time'] = datetime.utcnow()
        duration = (event['end_time'] - event['start_time']).total_seconds()
        event['duration'] = duration
        
        # Check if event meets minimum duration
        if duration >= self.min_duration:
            self.last_event_time[camera_id] = time.time()
            del self.active_events[camera_id]
            return event
        else:
            # Event too short, discard
            del self.active_events[camera_id]
            return None
            
    def is_event_active(self, camera_id):
        """Check if event is currently active"""
        return camera_id in self.active_events

