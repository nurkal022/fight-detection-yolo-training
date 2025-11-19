from ultralytics import YOLO
import cv2
import numpy as np
from datetime import datetime
import os
import threading
import json
from app.detection.event_manager import EventManager
from app.utils.logger import log_system

class UniversalDetector:
    """
    Universal detection class using any YOLO model.
    Handles video streams, detection, and event management.
    Configurable for any object detection classes.
    """
    
    def __init__(self, model_path, confidence_threshold=0.5, event_cooldown=5, 
                 detection_classes=None, event_type='detection'):
        """
        Initialize the detector.
        
        Args:
            model_path: Path to trained YOLO model
            confidence_threshold: Minimum confidence for detections
            event_cooldown: Seconds between logging duplicate events
            detection_classes: List of class names or indices to detect (None = all classes)
            event_type: Type of event to log (e.g., 'detection', 'intrusion', 'fight')
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.detection_classes = detection_classes
        self.event_type = event_type
        
        # Load model
        try:
            self.model = YOLO(model_path)
            log_system('INFO', f'Model loaded successfully from {model_path}', 'detector')
            
            # Get class names from model
            if hasattr(self.model, 'names'):
                self.class_names = self.model.names
                log_system('INFO', f'Available classes: {self.class_names}', 'detector')
            else:
                self.class_names = {}
                log_system('WARNING', 'Could not get class names from model', 'detector')
                
        except Exception as e:
            log_system('ERROR', f'Failed to load model: {str(e)}', 'detector')
            raise
        
        # Event manager for deduplication
        self.event_manager = EventManager(cooldown_seconds=event_cooldown)
        
        # Active streams
        self.active_streams = {}  # camera_id -> stream_data
        self.stream_threads = {}  # camera_id -> thread
        self.stream_locks = {}  # camera_id -> lock
        
        # Frame buffers for serving to web
        self.frame_buffers = {}  # camera_id -> latest_frame
        
        # Detection callbacks
        self.callbacks = []
        
        # Global lock
        self.lock = threading.Lock()
    
    def register_callback(self, callback):
        """Register a callback function for detection events."""
        with self.lock:
            self.callbacks.append(callback)
    
    def _trigger_callbacks(self, event_data):
        """Trigger all registered callbacks with event data."""
        with self.lock:
            for callback in self.callbacks:
                try:
                    callback(event_data)
                except Exception as e:
                    log_system('ERROR', f'Callback error: {str(e)}', 'detector')
    
    def _should_detect_class(self, class_id):
        """Check if we should detect this class."""
        if self.detection_classes is None:
            return True
        
        # Check if class_id is in detection_classes
        if isinstance(class_id, int):
            if class_id in self.detection_classes:
                return True
            # Check if class name is in detection_classes
            class_name = self.class_names.get(class_id, '')
            if class_name in self.detection_classes:
                return True
        
        return False
    
    def detect_frame(self, frame, camera_id=None):
        """
        Run detection on a single frame.
        
        Args:
            frame: Input frame (numpy array)
            camera_id: Optional camera ID for tracking
            
        Returns:
            tuple: (annotated_frame, detections_list, has_detection)
        """
        # Run inference
        results = self.model(frame, verbose=False)
        
        # Parse results
        detections = []
        has_detection = False
        detected_class = None
        max_confidence = 0.0
        
        for result in results:
            boxes = result.boxes
            keypoints = result.keypoints if hasattr(result, 'keypoints') else None
            
            for i, box in enumerate(boxes):
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                
                # Check if we should detect this class
                if not self._should_detect_class(cls):
                    continue
                
                # Check if confidence meets threshold
                if conf >= self.confidence_threshold:
                    has_detection = True
                    
                    # Get class name
                    class_name = self.class_names.get(cls, f'class_{cls}')
                    
                    # Track best detection
                    if conf > max_confidence:
                        max_confidence = conf
                        detected_class = class_name
                    
                    detection = {
                        'class': cls,
                        'class_name': class_name,
                        'confidence': conf,
                        'bbox': box.xyxy[0].cpu().numpy().tolist(),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    # Add keypoints if available
                    if keypoints is not None and len(keypoints) > i:
                        kpts = keypoints[i].xy.cpu().numpy()
                        detection['keypoints'] = kpts.tolist()
                    
                    detections.append(detection)
        
        # Get annotated frame
        annotated_frame = results[0].plot() if len(results) > 0 else frame
        
        # Update event manager
        if camera_id is not None:
            if has_detection:
                if not self.event_manager.is_event_active(camera_id):
                    # Start new event
                    event_data = self.event_manager.start_event(
                        camera_id, 
                        max_confidence,
                        annotated_frame.copy(),
                        detected_class
                    )
                    if event_data:
                        log_system('INFO', f'{detected_class} detected on camera {camera_id}', 'detector')
                else:
                    # Update existing event
                    self.event_manager.update_event(
                        camera_id,
                        max_confidence,
                        annotated_frame.copy(),
                        detected_class
                    )
            else:
                # No detection - check if we should end event
                if self.event_manager.is_event_active(camera_id):
                    event_data = self.event_manager.end_event(camera_id)
                    if event_data:
                        # Trigger callbacks with complete event
                        self._trigger_callbacks({
                            'camera_id': camera_id,
                            'event_type': self.event_type,
                            'detected_class': event_data.get('detected_class', 'unknown'),
                            'confidence': event_data['max_confidence'],
                            'start_time': event_data['start_time'],
                            'end_time': event_data['end_time'],
                            'duration': event_data['duration'],
                            'frame': event_data['best_frame'],
                            'detection_count': event_data['detection_count']
                        })
                        log_system('INFO', f'Detection ended on camera {camera_id}, duration: {event_data["duration"]:.2f}s', 'detector')
        
        return annotated_frame, detections, has_detection
    
    def start_stream(self, camera_id, source, source_type='webcam'):
        """
        Start processing a video stream.
        
        Args:
            camera_id: Unique camera identifier
            source: Video source (camera index, file path, or RTSP URL)
            source_type: Type of source ('webcam', 'file', 'rtsp')
        """
        if camera_id in self.active_streams:
            log_system('WARNING', f'Stream {camera_id} already active', 'detector')
            return False
        
        try:
            # Open video source
            log_system('INFO', f'Opening {source_type} source: {source}', 'detector')
            
            if source_type == 'webcam':
                cap = cv2.VideoCapture(int(source))
            else:
                cap = cv2.VideoCapture(source)
            
            # Wait a bit for camera to initialize
            import time
            time.sleep(0.5)
            
            if not cap.isOpened():
                log_system('ERROR', f'Failed to open {source_type} source: {source}', 'detector')
                return False
            
            # Try to read a test frame
            ret, test_frame = cap.read()
            if not ret or test_frame is None:
                log_system('ERROR', f'Cannot read from {source_type} source: {source}', 'detector')
                cap.release()
                return False
            
            log_system('INFO', f'Successfully opened {source_type} source: {source}, frame size: {test_frame.shape}', 'detector')
            
            # Store stream info
            stream_data = {
                'capture': cap,
                'source': source,
                'source_type': source_type,
                'active': True,
                'frame_count': 0,
                'detection_count': 0
            }
            
            self.active_streams[camera_id] = stream_data
            self.stream_locks[camera_id] = threading.Lock()
            
            # Start processing thread
            thread = threading.Thread(
                target=self._process_stream,
                args=(camera_id,),
                daemon=True
            )
            self.stream_threads[camera_id] = thread
            thread.start()
            
            log_system('INFO', f'Started stream {camera_id} from {source}', 'detector')
            return True
            
        except Exception as e:
            log_system('ERROR', f'Error starting stream {camera_id}: {str(e)}', 'detector')
            return False
    
    def _process_stream(self, camera_id):
        """
        Process video stream in a separate thread.
        
        Args:
            camera_id: Camera identifier
        """
        stream_data = self.active_streams[camera_id]
        cap = stream_data['capture']
        
        log_system('INFO', f'Processing thread started for camera {camera_id}', 'detector')
        
        while stream_data['active']:
            ret, frame = cap.read()
            
            if not ret:
                log_system('WARNING', f'Failed to read frame from camera {camera_id}', 'detector')
                # Try to reconnect for RTSP streams
                if stream_data['source_type'] == 'rtsp':
                    cap.release()
                    cap = cv2.VideoCapture(stream_data['source'])
                    stream_data['capture'] = cap
                    continue
                else:
                    break
            
            stream_data['frame_count'] += 1
            
            # Log first frame
            if stream_data['frame_count'] == 1:
                log_system('INFO', f'First frame captured for camera {camera_id}, shape: {frame.shape}', 'detector')
            
            # Run detection
            annotated_frame, detections, has_detection = self.detect_frame(frame, camera_id)
            
            if has_detection:
                stream_data['detection_count'] += 1
            
            # Store latest frame for serving
            with self.stream_locks[camera_id]:
                self.frame_buffers[camera_id] = annotated_frame.copy()
        
        # Clean up
        cap.release()
        log_system('INFO', f'Stream {camera_id} stopped', 'detector')
    
    def stop_stream(self, camera_id):
        """
        Stop processing a video stream.
        
        Args:
            camera_id: Camera identifier
        """
        if camera_id not in self.active_streams:
            return False
        
        # Mark stream as inactive
        self.active_streams[camera_id]['active'] = False
        
        # Wait for thread to finish
        if camera_id in self.stream_threads:
            self.stream_threads[camera_id].join(timeout=5)
            del self.stream_threads[camera_id]
        
        # Clean up
        if camera_id in self.active_streams:
            del self.active_streams[camera_id]
        if camera_id in self.frame_buffers:
            del self.frame_buffers[camera_id]
        if camera_id in self.stream_locks:
            del self.stream_locks[camera_id]
        
        # Reset event manager
        self.event_manager.reset_camera(camera_id)
        
        log_system('INFO', f'Stopped stream {camera_id}', 'detector')
        return True
    
    def get_latest_frame(self, camera_id):
        """
        Get the latest processed frame for a camera.
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            numpy array: Latest frame or None
        """
        if camera_id not in self.frame_buffers:
            return None
        
        with self.stream_locks[camera_id]:
            return self.frame_buffers[camera_id].copy()
    
    def get_stream_stats(self, camera_id):
        """Get statistics for a stream."""
        if camera_id not in self.active_streams:
            return None
        
        stream_data = self.active_streams[camera_id]
        return {
            'camera_id': camera_id,
            'active': stream_data['active'],
            'frame_count': stream_data['frame_count'],
            'detection_count': stream_data['detection_count'],
            'source': stream_data['source'],
            'source_type': stream_data['source_type']
        }
    
    def get_all_stats(self):
        """Get statistics for all active streams."""
        return {
            'active_streams': len(self.active_streams),
            'streams': [self.get_stream_stats(cid) for cid in self.active_streams.keys()],
            'event_stats': self.event_manager.get_statistics()
        }
    
    def cleanup(self):
        """Stop all streams and cleanup resources."""
        camera_ids = list(self.active_streams.keys())
        for camera_id in camera_ids:
            self.stop_stream(camera_id)
        
        log_system('INFO', 'Detector cleanup complete', 'detector')


