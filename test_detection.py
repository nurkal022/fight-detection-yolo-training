"""
Test detection script for quick testing without web interface
"""
from ultralytics import YOLO
import cv2

def test_model():
    """Test your model configuration"""
    
    print("="*60)
    print("Testing Detection Configuration")
    print("="*60)
    
    # Load model - try trained model first, fallback to base model
    import os
    best_model = 'fight_detection/fight_detection_yolo11n2/weights/best.pt'
    if os.path.exists(best_model):
        model_path = best_model
    else:
        # Try last.pt
        last_model = 'fight_detection/fight_detection_yolo11n2/weights/last.pt'
        if os.path.exists(last_model):
            model_path = last_model
        else:
            model_path = 'yolo11n.pt'
    
    print(f"\nLoading model: {model_path}")
    
    try:
        model = YOLO(model_path)
        print("✅ Model loaded successfully!")
        
        # Print available classes
        print(f"\n📋 Available classes ({len(model.names)}):")
        for idx, name in model.names.items():
            print(f"  {idx}: {name}")
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return
    
    # Test on webcam or image
    print("\n" + "="*60)
    print("Testing detection...")
    print("="*60)
    
    # Option 1: Test on image
    # results = model('test_image.jpg')
    # results[0].show()
    
    # Option 2: Test on webcam
    print("\nOpening webcam (press 'q' to quit)...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Cannot open webcam")
        return
    
    print("✅ Webcam opened")
    print("Press 'q' to quit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Run detection on GPU
        results = model(frame, verbose=False, device='cuda')
        
        # Get annotated frame
        annotated_frame = results[0].plot()
        
        # Display
        cv2.imshow('Detection Test', annotated_frame)
        
        # Quit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Test completed!")

if __name__ == '__main__':
    test_model()


