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
                 detection_classes=None, event_type='detection', min_duration=1):
        """
        Initialize the detector.
        
        Args:
            model_path: Path to trained YOLO model
            confidence_threshold: Minimum confidence for detections
            event_cooldown: Seconds between logging duplicate events
            detection_classes: List of class names or indices to detect (None = all classes)
            event_type: Type of event to log (e.g., 'detection', 'intrusion', 'fight')
            min_duration: Minimum duration in seconds to consider an event valid
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.detection_classes = detection_classes
        self.event_type = event_type
        
        # Load model
        try:
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = YOLO(model_path)
            log_system('INFO', f'Model loaded successfully from {model_path} (device: {device})', 'detector')
            
            # Get class names from model
            if hasattr(self.model, 'names'):
                self.class_names = self.model.names
                log_system('INFO', f'Available classes: {self.class_names}', 'detector')
            else:
                self.class_names = {}
                log_system('WARNING', 'Could not get class names from model', 'detector')
            
            self.device = device
                
        except Exception as e:
            log_system('ERROR', f'Failed to load model: {str(e)}', 'detector')
            raise
        
        # Event manager for deduplication
        self.event_manager = EventManager(cooldown_seconds=event_cooldown, min_duration=min_duration)
        
        # Active streams
        self.active_streams = {}  # camera_id -> stream_data
        self.stream_threads = {}  # camera_id -> thread
        self.stream_locks = {}  # camera_id -> lock
        
        # Frame buffers for serving to web
        self.frame_buffers = {}  # camera_id -> latest_frame
        self.frame_timestamps = {}  # camera_id -> timestamp of last frame update
        self.frame_buffer_locks = {}  # camera_id -> lock for frame buffer access
        
        # Last detections per camera (for smooth display without flickering)
        self.last_detections = {}  # camera_id -> list of detections
        
        # Last original frames per camera (for drawing detections on latest frame)
        self.last_original_frames = {}  # camera_id -> latest original frame
        
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
    
    def _draw_detections_safe(self, frame, detections):
        """
        Draw bounding boxes on frame with safe boundary checking.
        
        Args:
            frame: Input frame (numpy array)
            detections: List of detection dicts with 'bbox', 'class_name', 'confidence'
            
        Returns:
            numpy array: Frame with drawn bounding boxes
        """
        annotated_frame = frame.copy()
        h, w = frame.shape[:2]
        
        for det in detections:
            bbox = det.get('bbox', [])
            if len(bbox) != 4:
                continue
            
            x1, y1, x2, y2 = bbox
            
            # Clamp coordinates to frame boundaries
            x1 = max(0, min(int(x1), w - 1))
            y1 = max(0, min(int(y1), h - 1))
            x2 = max(0, min(int(x2), w - 1))
            y2 = max(0, min(int(y2), h - 1))
            
            # Skip if box is invalid after clamping
            if x2 <= x1 or y2 <= y1:
                continue
            
            # Get class info
            class_name = det.get('class_name', 'unknown')
            confidence = det.get('confidence', 0.0)
            
            # Draw bounding box
            color = (0, 255, 0)  # Green
            thickness = 2
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label with background
            label = f'{class_name} {confidence:.2f}'
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            font_thickness = 2
            
            # Get text size
            (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)
            
            # Draw background rectangle for text
            text_x = x1
            text_y = max(y1 - 10, text_height + 10)
            cv2.rectangle(annotated_frame, 
                          (text_x, text_y - text_height - 5), 
                          (text_x + text_width, text_y + baseline), 
                          (0, 0, 0), -1)
            
            # Draw text
            cv2.putText(annotated_frame, label, (text_x, text_y), 
                       font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
        
        return annotated_frame
    
    def detect_frame(self, frame, camera_id=None):
        """
        Run detection on a single frame.
        Optimized for performance.
        
        Args:
            frame: Input frame (numpy array) - may be resized for performance
            camera_id: Optional camera ID for tracking
            
        Returns:
            tuple: (annotated_frame, detections_list, has_detection)
            Note: annotated_frame is same size as input frame, detections bbox coordinates are in input frame coordinates
        """
        original_frame = frame
        
        # Run inference (use device from initialization)
        # Use imgsz=640 since frame is already resized to 640px width
        results = self.model(frame, verbose=False, device=self.device, imgsz=640)
        
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
                    
                    # Get bbox coordinates (in frame coordinates)
                    bbox_coords = box.xyxy[0].cpu().numpy().tolist()
                    
                    detection = {
                        'class': cls,
                        'class_name': class_name,
                        'confidence': conf,
                        'bbox': bbox_coords,  # Coordinates in input frame size
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    # Add keypoints if available
                    if keypoints is not None and len(keypoints) > i:
                        kpts = keypoints[i].xy.cpu().numpy()
                        detection['keypoints'] = kpts.tolist()
                    
                    detections.append(detection)
        
        # Get annotated frame with safe bounding box drawing
        if len(detections) > 0:
            # Use safe drawing function to prevent out-of-bounds errors
            annotated_frame = self._draw_detections_safe(original_frame, detections)
        else:
            annotated_frame = original_frame
        
        # Update event manager (optimized - only copy frame when starting event)
        if camera_id is not None:
            if has_detection:
                if not self.event_manager.is_event_active(camera_id):
                    # Start new event (copy frame only for event, not for update)
                    event_data = self.event_manager.start_event(
                        camera_id, 
                        max_confidence,
                        annotated_frame.copy() if annotated_frame is not None else None,
                        detected_class
                    )
                    if event_data:
                        log_system('INFO', f'{detected_class} detected on camera {camera_id}', 'detector')
                else:
                    # Update existing event (no frame copy to save time)
                    self.event_manager.update_event(
                        camera_id,
                        max_confidence,
                        None,  # Don't copy frame on every update
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
            self.frame_buffer_locks[camera_id] = threading.Lock()
            
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
        import time
        
        stream_data = self.active_streams[camera_id]
        cap = stream_data['capture']
        
        log_system('INFO', f'Processing thread started for camera {camera_id}', 'detector')
        
        consecutive_failures = 0
        max_failures = 10
        
        while stream_data['active']:
            ret, frame = cap.read()
            
            if not ret or frame is None:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    log_system('ERROR', f'Too many consecutive failures reading from camera {camera_id}, stopping stream', 'detector')
                    break
                
                log_system('WARNING', f'Failed to read frame from camera {camera_id} (attempt {consecutive_failures}/{max_failures})', 'detector')
                # Try to reconnect for RTSP streams
                if stream_data['source_type'] == 'rtsp':
                    cap.release()
                    time.sleep(1)
                    cap = cv2.VideoCapture(stream_data['source'])
                    stream_data['capture'] = cap
                else:
                    time.sleep(0.1)
                continue
            
            consecutive_failures = 0  # Reset on success
            
            stream_data['frame_count'] += 1
            
            # Log first frame
            if stream_data['frame_count'] == 1:
                log_system('INFO', f'First frame captured for camera {camera_id}, shape: {frame.shape}', 'detector')
            
            # CRITICAL: Save original frame (before detection)
            # This ensures smooth video even if detection is slow
            self.last_original_frames[camera_id] = frame.copy()
            
            # Draw last detections on current frame for smooth display (if available)
            if camera_id in self.last_detections and len(self.last_detections[camera_id]) > 0:
                display_frame = self._draw_detections_safe(frame, self.last_detections[camera_id])
            else:
                display_frame = frame
            
            # Update frame buffer immediately with lock for thread safety
            with self.frame_buffer_locks[camera_id]:
            self.frame_buffers[camera_id] = display_frame
            self.frame_timestamps[camera_id] = time.time()
            
            # Run detection in background (non-blocking for frame updates)
            try:
                # Resize frame for faster detection if needed
                detection_frame = frame.copy()  # Copy to avoid modifying original
                scale_factor = 1.0
                if frame.shape[1] > 640:
                    scale_factor = 640 / frame.shape[1]
                    detection_frame = cv2.resize(detection_frame, (640, int(frame.shape[0] * scale_factor)))
                
                # Run detection (this may take time, but frame buffer already updated)
                annotated_frame, detections, has_detection = self.detect_frame(detection_frame, camera_id)
                
                # Scale detections back to original frame size if frame was resized
                scaled_detections = []
                if has_detection:
                    for det in detections:
                        scaled_det = det.copy()
                        if 'bbox' in scaled_det and len(scaled_det['bbox']) == 4:
                            # Scale bbox coordinates back to original frame size
                            scaled_det['bbox'] = [coord / scale_factor for coord in scaled_det['bbox']]
                        scaled_detections.append(scaled_det)
                    
                    # Save scaled detections for future frames
                    self.last_detections[camera_id] = scaled_detections
                    stream_data['detection_count'] += 1
                    
                    # Update frame buffer with new detections on latest original frame
                    # Use last saved original frame (may be newer than the one used for detection)
                    latest_original = self.last_original_frames.get(camera_id, frame)
                    display_frame_with_detections = self._draw_detections_safe(latest_original, scaled_detections)
                    
                    with self.frame_buffer_locks[camera_id]:
                    self.frame_buffers[camera_id] = display_frame_with_detections
                    self.frame_timestamps[camera_id] = time.time()
                else:
                    # No detections - clear saved detections
                    if camera_id in self.last_detections:
                        self.last_detections[camera_id] = []
                
                # Check for event timeouts (auto-end long-running events) - only every 30 frames to reduce overhead
                if stream_data['frame_count'] % 30 == 0 and self.event_manager.is_event_active(camera_id):
                    timeout_event = self.event_manager.check_timeout(camera_id, timeout_seconds=3, max_duration=10)
                    if timeout_event:
                        # Trigger callback for timed-out event (in separate thread to not block)
                        import threading
                        def send_timeout_event():
                            self._trigger_callbacks({
                                'camera_id': camera_id,
                                'event_type': self.event_type,
                                'detected_class': timeout_event.get('detected_class', 'unknown'),
                                'confidence': timeout_event['max_confidence'],
                                'start_time': timeout_event['start_time'],
                                'end_time': timeout_event['end_time'],
                                'duration': timeout_event['duration'],
                                'frame': timeout_event['best_frame'],
                                'detection_count': timeout_event['detection_count']
                            })
                        threading.Thread(target=send_timeout_event, daemon=True).start()
                        log_system('INFO', f'Event auto-ended on camera {camera_id} (timeout), duration: {timeout_event["duration"]:.2f}s', 'detector')
            except Exception as e:
                log_system('ERROR', f'Error processing frame for camera {camera_id}: {str(e)}', 'detector')
                import traceback
                log_system('ERROR', f'Traceback: {traceback.format_exc()}', 'detector')
                # On error, still update frame buffer with original frame
                with self.frame_buffer_locks[camera_id]:
                self.frame_buffers[camera_id] = frame
                self.frame_timestamps[camera_id] = time.time()
                time.sleep(0.001)
            
            # Minimal delay to prevent CPU overload but maintain smooth FPS
            time.sleep(0.001)
        
        # End any active events before cleanup
        if self.event_manager.is_event_active(camera_id):
            final_event = self.event_manager.end_event(camera_id)
            if final_event:
                self._trigger_callbacks({
                    'camera_id': camera_id,
                    'event_type': self.event_type,
                    'detected_class': final_event.get('detected_class', 'unknown'),
                    'confidence': final_event['max_confidence'],
                    'start_time': final_event['start_time'],
                    'end_time': final_event['end_time'],
                    'duration': final_event['duration'],
                    'frame': final_event['best_frame'],
                    'detection_count': final_event['detection_count']
                })
        
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
        if camera_id in self.frame_timestamps:
            del self.frame_timestamps[camera_id]
        if camera_id in self.stream_locks:
            del self.stream_locks[camera_id]
        if camera_id in self.frame_buffer_locks:
            del self.frame_buffer_locks[camera_id]
        
        # Reset event manager
        self.event_manager.reset_camera(camera_id)
        
        log_system('INFO', f'Stopped stream {camera_id}', 'detector')
        return True
    
    def get_latest_frame(self, camera_id):
        """
        Get the latest processed frame for a camera.
        Thread-safe with minimal blocking - copies frame quickly.
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            numpy array: Latest frame copy or None
        """
        if camera_id not in self.frame_buffers:
            return None
        
        if camera_id not in self.frame_buffer_locks:
            return None
        
        try:
            # Get frame with lock - copy immediately to minimize lock time
            with self.frame_buffer_locks[camera_id]:
            frame = self.frame_buffers.get(camera_id)
            if frame is not None:
                    # Copy immediately while holding lock (fast operation)
                return frame.copy()
            return None
        except Exception as e:
            # Return None on any error to prevent blocking
            return None
    
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


