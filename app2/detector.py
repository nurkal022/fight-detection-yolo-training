"""
Standalone YOLO detector for native application
"""
from ultralytics import YOLO
import cv2
import numpy as np
import torch
from datetime import datetime
import time


class StandaloneDetector:
    """Standalone YOLO detector without Flask dependencies"""
    
    def __init__(self, model_path, confidence_threshold=0.65, detection_classes=None):
        """
        Initialize detector.
        
        Args:
            model_path: Path to YOLO model
            confidence_threshold: Minimum confidence for detections
            detection_classes: List of class indices to detect (None = all)
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.detection_classes = detection_classes
        
        # Load model
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Loading model from {model_path}...")
        self.model = YOLO(model_path)
        self.device = device
        
        # Get class names
        if hasattr(self.model, 'names'):
            self.class_names = self.model.names
            print(f"Available classes: {self.class_names}")
        else:
            self.class_names = {}
            
    def detect(self, frame):
        """
        Run detection on a frame.
        
        Args:
            frame: Input frame (numpy array)
            
        Returns:
            tuple: (annotated_frame, detections_list, has_detection)
        """
        # Run inference
        results = self.model(frame, verbose=False, device=self.device, imgsz=640)
        
        # Parse results
        detections = []
        has_detection = False
        annotated_frame = frame.copy()
        
        for result in results:
            boxes = result.boxes
            
            for box in boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                
                # Check if we should detect this class
                if self.detection_classes is not None and cls not in self.detection_classes:
                    continue
                
                # Check confidence threshold
                if conf >= self.confidence_threshold:
                    has_detection = True
                    
                    # Get class name
                    class_name = self.class_names.get(cls, f'class_{cls}')
                    
                    # Get bbox coordinates
                    bbox_coords = box.xyxy[0].cpu().numpy().tolist()
                    
                    detection = {
                        'class': cls,
                        'class_name': class_name,
                        'confidence': conf,
                        'bbox': bbox_coords,
                    }
                    
                    detections.append(detection)
                    
                    # Draw bounding box
                    x1, y1, x2, y2 = [int(c) for c in bbox_coords]
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw label
                    label = f'{class_name} {conf:.2f}'
                    (text_width, text_height), baseline = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                    )
                    cv2.rectangle(annotated_frame,
                                (x1, y1 - text_height - 5),
                                (x1 + text_width, y1),
                                (0, 0, 0), -1)
                    cv2.putText(annotated_frame, label, (x1, y1 - 5),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return annotated_frame, detections, has_detection

