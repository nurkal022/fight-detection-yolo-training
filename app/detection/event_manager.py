from datetime import datetime, timedelta
from collections import defaultdict
import threading
import json

class EventManager:
    """
    Manages detection events and prevents duplication.
    Implements cooldown periods and event aggregation.
    """
    
    def __init__(self, cooldown_seconds=5, min_duration=1):
        """
        Args:
            cooldown_seconds: Minimum seconds between logging same event type
            min_duration: Minimum duration in seconds to consider an event valid
        """
        self.cooldown_seconds = cooldown_seconds
        self.min_duration = min_duration
        
        # Track last event time per camera
        self.last_event_time = defaultdict(lambda: None)
        
        # Track active events (ongoing detections)
        self.active_events = {}  # camera_id -> event_data
        
        # Track event start times
        self.event_start_times = {}  # camera_id -> start_time
        
        # Thread lock for thread-safe operations
        self.lock = threading.Lock()
    
    def should_log_event(self, camera_id, confidence):
        """
        Determine if a detection should be logged as an event.
        
        Args:
            camera_id: ID of the camera/source
            confidence: Detection confidence score
            
        Returns:
            bool: True if event should be logged
        """
        with self.lock:
            current_time = datetime.utcnow()
            
            # Check if we're in cooldown period
            last_time = self.last_event_time.get(camera_id)
            if last_time:
                time_since_last = (current_time - last_time).total_seconds()
                if time_since_last < self.cooldown_seconds:
                    return False
            
            return True
    
    def start_event(self, camera_id, confidence, frame_data=None, detected_class=None):
        """
        Start tracking a new event.
        
        Args:
            camera_id: ID of the camera/source
            confidence: Detection confidence score
            frame_data: Optional frame image data
            detected_class: Name of detected class
            
        Returns:
            dict: Event data if started, None otherwise
        """
        with self.lock:
            if camera_id in self.active_events:
                # Event already active, update confidence if higher
                if confidence > self.active_events[camera_id]['max_confidence']:
                    self.active_events[camera_id]['max_confidence'] = confidence
                    if frame_data is not None:
                        self.active_events[camera_id]['best_frame'] = frame_data
                    if detected_class:
                        self.active_events[camera_id]['detected_class'] = detected_class
                return None
            
            # Start new event
            current_time = datetime.utcnow()
            event_data = {
                'camera_id': camera_id,
                'start_time': current_time,
                'max_confidence': confidence,
                'detection_count': 1,
                'best_frame': frame_data,
                'detected_class': detected_class
            }
            
            self.active_events[camera_id] = event_data
            self.event_start_times[camera_id] = current_time
            
            return event_data
    
    def update_event(self, camera_id, confidence, frame_data=None, detected_class=None):
        """
        Update an ongoing event.
        
        Args:
            camera_id: ID of the camera/source
            confidence: Detection confidence score
            frame_data: Optional frame image data
            detected_class: Name of detected class
        """
        with self.lock:
            if camera_id not in self.active_events:
                return
            
            self.active_events[camera_id]['detection_count'] += 1
            
            # Update best confidence and frame
            if confidence > self.active_events[camera_id]['max_confidence']:
                self.active_events[camera_id]['max_confidence'] = confidence
                if frame_data is not None:
                    self.active_events[camera_id]['best_frame'] = frame_data
                if detected_class:
                    self.active_events[camera_id]['detected_class'] = detected_class
    
    def end_event(self, camera_id):
        """
        End an active event and determine if it should be logged.
        
        Args:
            camera_id: ID of the camera/source
            
        Returns:
            dict: Event data to log if valid, None otherwise
        """
        with self.lock:
            if camera_id not in self.active_events:
                return None
            
            event_data = self.active_events[camera_id]
            start_time = self.event_start_times[camera_id]
            end_time = datetime.utcnow()
            
            duration = (end_time - start_time).total_seconds()
            
            # Clean up
            del self.active_events[camera_id]
            del self.event_start_times[camera_id]
            
            # Check if event meets minimum duration
            if duration < self.min_duration:
                return None
            
            # Check cooldown
            if not self.should_log_event(camera_id, event_data['max_confidence']):
                return None
            
            # Update last event time
            self.last_event_time[camera_id] = end_time
            
            # Prepare event data for logging
            event_data['end_time'] = end_time
            event_data['duration'] = duration
            
            return event_data
    
    def check_timeout(self, camera_id, timeout_seconds=3):
        """
        Check if an active event has timed out (no detections for timeout period).
        
        Args:
            camera_id: ID of the camera/source
            timeout_seconds: Seconds without detection to consider event ended
            
        Returns:
            dict: Event data if timed out, None otherwise
        """
        with self.lock:
            if camera_id not in self.active_events:
                return None
            
            start_time = self.event_start_times[camera_id]
            current_time = datetime.utcnow()
            
            # For simplicity, we'll end the event if it's been going for a while
            # In practice, you'd track the last detection time
            duration = (current_time - start_time).total_seconds()
            
            if duration > timeout_seconds:
                return self.end_event(camera_id)
            
            return None
    
    def is_event_active(self, camera_id):
        """Check if there's an active event for a camera."""
        with self.lock:
            return camera_id in self.active_events
    
    def get_active_event(self, camera_id):
        """Get active event data for a camera."""
        with self.lock:
            return self.active_events.get(camera_id)
    
    def reset_camera(self, camera_id):
        """Reset all tracking for a specific camera."""
        with self.lock:
            if camera_id in self.active_events:
                del self.active_events[camera_id]
            if camera_id in self.event_start_times:
                del self.event_start_times[camera_id]
            if camera_id in self.last_event_time:
                del self.last_event_time[camera_id]
    
    def get_statistics(self):
        """Get current statistics."""
        with self.lock:
            return {
                'active_events': len(self.active_events),
                'cameras_with_history': len(self.last_event_time),
                'active_cameras': list(self.active_events.keys())
            }


