#!/usr/bin/env python3
"""
Script to detect objects in images and save annotated results
"""
import cv2
import os
from ultralytics import YOLO
import torch
import numpy as np
from datetime import datetime

def detect_and_save_images():
    """Detect objects in sample images and save annotated results"""

    print("="*60)
    print("Detection on Sample Images")
    print("="*60)

    # Model path - same as in app/config.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, 'fight_detection/fight_detection_yolo11n2/weights/best.pt')

    print(f"\nLoading model: {model_path}")

    # Load model
    try:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = YOLO(model_path)
        print(f"✅ Model loaded successfully! (device: {device})")

        # Print available classes
        print(f"\n📋 Available classes ({len(model.names)}):")
        for idx, name in model.names.items():
            print(f"  {idx}: {name}")

    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return

    # Image directory
    image_dir = 'samples/custom'
    if not os.path.exists(image_dir):
        print(f"❌ Image directory not found: {image_dir}")
        return

    # Get image files
    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not image_files:
        print(f"❌ No image files found in {image_dir}")
        return

    print(f"\n📸 Found {len(image_files)} images to process:")
    for img_file in image_files:
        print(f"  - {img_file}")

    # Process each image
    for image_file in image_files:
        image_path = os.path.join(image_dir, image_file)

        print(f"\n🔍 Processing: {image_file}")

        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                print(f"❌ Could not read image: {image_path}")
                continue

            print(f"  📐 Image size: {image.shape[1]}x{image.shape[0]}")

            # Run detection with lower confidence threshold
            results = model(image, verbose=False, device=device, conf=0.01)

            # Get annotated image
            annotated_image = results[0].plot()

            # Get detections info
            detections = results[0].boxes
            if len(detections) > 0:
                print(f"  🎯 Found {len(detections)} detections:")

                # Group detections by class
                class_counts = {}
                for detection in detections:
                    class_id = int(detection.cls.item())
                    confidence = detection.conf.item()
                    class_name = model.names[class_id]

                    if class_name not in class_counts:
                        class_counts[class_name] = []
                    class_counts[class_name].append(confidence)

                # Print summary
                for class_name, confidences in class_counts.items():
                    avg_conf = sum(confidences) / len(confidences)
                    print(f"    {class_name}: {len(confidences)} detections (avg conf: {avg_conf:.2f})")
            else:
                print("  ⚠️  No detections found")

            # Save annotated image (overwrite original)
            success = cv2.imwrite(image_path, annotated_image)
            if success:
                print(f"  💾 Saved annotated image: {image_path}")
            else:
                print(f"❌ Failed to save: {image_path}")

        except Exception as e:
            print(f"❌ Error processing {image_file}: {str(e)}")
            continue

    print(f"\n✅ Processing completed!")
    print(f"📁 Annotated images saved in: {image_dir}")

if __name__ == '__main__':
    detect_and_save_images()
