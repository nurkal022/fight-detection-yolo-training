"""
Main display application using pygame - Standalone version
"""
import pygame
import sys
import os
import time
import threading
import math
import cv2
import numpy as np
from datetime import datetime
from config import *
from detector import StandaloneDetector
from event_manager import EventManager
from notifier import Notifier


class DetectionDisplay:
    """Main application window for displaying detection stream"""
    
    def __init__(self, camera_index=0):
        """Initialize display application"""
        self.camera_index = camera_index
        self.running = False
        
        # Initialize pygame
        pygame.init()
        pygame.mixer.init()  # For sound alerts
        
        # Create window
        if FULLSCREEN:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        
        pygame.display.set_caption(f'Fight Detection - Camera {camera_index}')
        
        # Initialize font
        try:
            self.font_small = pygame.font.Font(None, FONT_SIZE_SMALL)
            self.font_medium = pygame.font.Font(None, FONT_SIZE_MEDIUM)
            self.font_large = pygame.font.Font(None, FONT_SIZE_LARGE)
        except:
            # Fallback to default font
            self.font_small = pygame.font.Font(pygame.font.get_default_font(), FONT_SIZE_SMALL)
            self.font_medium = pygame.font.Font(pygame.font.get_default_font(), FONT_SIZE_MEDIUM)
            self.font_large = pygame.font.Font(pygame.font.get_default_font(), FONT_SIZE_LARGE)
        
        # Initialize detector
        print(f"Initializing detector with model: {MODEL_PATH}")
        self.detector = StandaloneDetector(
            MODEL_PATH,
            confidence_threshold=CONFIDENCE_THRESHOLD,
            detection_classes=DETECTION_CLASSES
        )
        
        # Initialize event manager
        self.event_manager = EventManager(
            cooldown_seconds=EVENT_COOLDOWN,
            min_duration=EVENT_MIN_DURATION
        )
        
        # Initialize notifier
        self.notifier = Notifier()
        if self.notifier.enabled:
            print("✓ Telegram notifications enabled")
        else:
            print("⚠️ Telegram notifications disabled (check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
        
        # Initialize camera
        print(f"Opening camera {camera_index}...")
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera {camera_index}")
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        
        # Get actual frame size
        ret, test_frame = self.cap.read()
        if ret:
            h, w = test_frame.shape[:2]
            print(f"Camera opened: {w}x{h}")
        else:
            raise RuntimeError("Cannot read from camera")
        
        # Frame processing
        self.current_frame = None
        self.frame_timestamp = 0
        self.processing_thread = None
        
        # Stats
        self.stats = {
            'frame_count': 0,
            'fps': 0,
            'last_detection': None,
            'detection_count': 0,
            'current_detections': [],
        }
        self.last_fps_update = time.time()
        self.fps_frames = 0
        
        # Notifications
        self.notifications = []
        self.last_detection_time = None
        
        # Notification sending state
        self.sending_notification = False
        self.notification_send_start_time = None
        self.notification_send_event = None
        self.notification_sent_successfully = False
        self.notification_send_end_time = None
        
        # Clock for FPS control
        self.clock = pygame.time.Clock()
        
    def _process_frame_loop(self):
        """Background thread for processing frames"""
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    time.sleep(0.1)
                    continue
                
                # Run detection
                annotated_frame, detections, has_detection = self.detector.detect(frame)
                
                # Update frame
                self.current_frame = annotated_frame
                self.frame_timestamp = time.time()
                self.fps_frames += 1
                self.stats['frame_count'] += 1
                self.stats['current_detections'] = detections
                
                # Handle events
                if has_detection:
                    # Get best detection
                    best_detection = max(detections, key=lambda d: d['confidence'])
                    detected_class = best_detection['class_name']
                    confidence = best_detection['confidence']
                    
                    # Check if event is active
                    if self.event_manager.is_event_active(self.camera_index):
                        # Update existing event
                        self.event_manager.update_event(self.camera_index, confidence, detected_class)
                    else:
                        # Start new event
                        event_data = self.event_manager.start_event(
                            self.camera_index, detected_class, confidence
                        )
                        if event_data:
                            print(f"🔴 Detection started: {detected_class} ({confidence:.2f})")
                else:
                    # No detection - end event if active
                    if self.event_manager.is_event_active(self.camera_index):
                        event_data = self.event_manager.end_event(self.camera_index)
                        if event_data:
                            self.stats['last_detection'] = event_data
                            self.stats['detection_count'] += 1
                            
                            print(f"✓ Event ended: {event_data['detected_class']} "
                                  f"({event_data['duration']:.1f}s, {event_data['detection_count']} detections)")
                            
                            # Show notification
                            if NOTIFICATIONS_ENABLED:
                                self._show_notification(event_data)
                            
                            # Play sound
                            if ALERT_SOUND_ENABLED:
                                self._play_alert_sound()
                            
                            # Send Telegram notification with visualization
                            if self.notifier.enabled:
                                self.sending_notification = True
                                self.notification_send_start_time = time.time()
                                self.notification_send_event = event_data
                                print(f"📤 Preparing to send Telegram notification for: {event_data['detected_class']}")
                                
                                # Send in background thread to show progress
                                def send_with_visualization():
                                    try:
                                        self.notifier.send_notification(event_data)
                                        self.notification_sent_successfully = True
                                    except Exception as e:
                                        self.notification_sent_successfully = False
                                        print(f"Error sending notification: {e}")
                                    finally:
                                        self.notification_send_end_time = time.time()
                                        # Show success/failure for 2 seconds
                                        time.sleep(2)
                                        self.sending_notification = False
                                        self.notification_send_start_time = None
                                        self.notification_send_event = None
                                        self.notification_sent_successfully = False
                                        self.notification_send_end_time = None
                                
                                threading.Thread(target=send_with_visualization, daemon=True).start()
                            else:
                                print(f"⚠️ Telegram notifications disabled (enabled={self.notifier.enabled})")
                
                # Small delay to prevent CPU overload
                time.sleep(0.001)
                
            except Exception as e:
                print(f"Error processing frame: {e}")
                time.sleep(0.1)
                
    def _show_notification(self, event):
        """Show on-screen notification"""
        detected_class = event.get('detected_class', 'Unknown')
        confidence = event.get('max_confidence', 0.0)
        
        notification = {
            'text': f'{detected_class} detected ({confidence*100:.0f}%)',
            'timestamp': time.time(),
            'duration': NOTIFICATION_DURATION,
        }
        
        self.notifications.append(notification)
        
        # Keep only last 3 notifications
        if len(self.notifications) > 3:
            self.notifications.pop(0)
            
    def _play_alert_sound(self):
        """Play alert sound"""
        try:
            if ALERT_SOUND_FILE and os.path.exists(ALERT_SOUND_FILE):
                pygame.mixer.music.load(ALERT_SOUND_FILE)
                pygame.mixer.music.play()
            else:
                # Generate beep sound using numpy
                duration = 0.2
                frequency = 800
                sample_rate = 22050
                frames = int(duration * sample_rate)
                arr = np.zeros((frames, 2), dtype=np.int16)
                max_sample = 2**(16 - 1) - 1
                for i in range(frames):
                    wave = max_sample * math.sin(2 * math.pi * frequency * i / sample_rate)
                    arr[i] = [int(wave), int(wave)]
                sound = pygame.sndarray.make_sound(arr)
                sound.play()
        except Exception as e:
            print(f"Error playing sound: {e}")
            
    def _draw_frame(self):
        """Draw current frame"""
        if self.current_frame is None:
            # Draw "No frame" message
            text = self.font_large.render("No frame", True, COLORS['text'])
            text_rect = text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2))
            self.screen.blit(text, text_rect)
            return
            
        # Convert BGR to RGB (OpenCV uses BGR, pygame expects RGB)
        frame_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
        
        # Resize frame to fit window
        frame_height, frame_width = frame_rgb.shape[:2]
        scale = min(WINDOW_WIDTH / frame_width, WINDOW_HEIGHT / frame_height)
        new_width = int(frame_width * scale)
        new_height = int(frame_height * scale)
        
        # Convert numpy array to pygame surface
        # pygame.surfarray expects (W, H, 3) format
        frame_swapped = np.transpose(frame_rgb, (1, 0, 2))
        frame_surface = pygame.surfarray.make_surface(frame_swapped)
        
        # Resize if needed
        if new_width != frame_width or new_height != frame_height:
            frame_surface = pygame.transform.scale(frame_surface, (new_width, new_height))
        
        # Center frame
        x = (WINDOW_WIDTH - new_width) // 2
        y = (WINDOW_HEIGHT - new_height) // 2
        self.screen.blit(frame_surface, (x, y))
        
    def _draw_stats(self):
        """Draw statistics overlay"""
        if not SHOW_STATS:
            return
            
        y_offset = 10
        x_offset = 10
        
        # FPS
        fps_text = self.font_small.render(f'FPS: {self.stats["fps"]}', True, COLORS['info'])
        self.screen.blit(fps_text, (x_offset, y_offset))
        y_offset += 25
        
        # Frame count
        frame_text = self.font_small.render(f'Frames: {self.stats["frame_count"]}', True, COLORS['info'])
        self.screen.blit(frame_text, (x_offset, y_offset))
        y_offset += 25
        
        # Detection count
        det_text = self.font_small.render(f'Detections: {self.stats["detection_count"]}', True, COLORS['success'])
        self.screen.blit(det_text, (x_offset, y_offset))
        y_offset += 25
        
        # Current detections
        if self.stats['current_detections']:
            for det in self.stats['current_detections'][:3]:  # Show max 3
                class_name = det['class_name']
                confidence = det['confidence']
                det_info = f'{class_name}: {confidence*100:.0f}%'
                det_info_text = self.font_small.render(det_info, True, COLORS['detection_text'])
                self.screen.blit(det_info_text, (x_offset, y_offset))
                y_offset += 20
        
        # Last detection
        if self.stats['last_detection']:
            last_det = self.stats['last_detection']
            class_name = last_det.get('detected_class', 'Unknown')
            confidence = last_det.get('max_confidence', 0.0)
            duration = last_det.get('duration', 0.0)
            det_info = f'Last: {class_name} ({confidence*100:.0f}%, {duration:.1f}s)'
            det_info_text = self.font_small.render(det_info, True, COLORS['detection_text'])
            self.screen.blit(det_info_text, (x_offset, y_offset))
            
    def _draw_notifications(self):
        """Draw notification overlay"""
        current_time = time.time()
        y_offset = WINDOW_HEIGHT - 150
        
        # Remove expired notifications
        self.notifications = [n for n in self.notifications 
                            if current_time - n['timestamp'] < n['duration']]
        
        # Draw notifications
        for notification in reversed(self.notifications):
            elapsed = current_time - notification['timestamp']
            alpha = max(0, 255 - int((elapsed / notification['duration']) * 255))
            
            text = self.font_medium.render(notification['text'], True, COLORS['alert'])
            
            # Draw background
            bg_rect = pygame.Rect(10, y_offset - 5, text.get_width() + 20, text.get_height() + 10)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(alpha)
            bg_surface.fill((0, 0, 0))
            self.screen.blit(bg_surface, bg_rect)
            
            # Draw text
            text.set_alpha(alpha)
            self.screen.blit(text, (20, y_offset))
            y_offset -= 40
    
    def _draw_sending_indicator(self):
        """Draw indicator when sending Telegram notification"""
        if not self.sending_notification or not self.notification_send_event:
            return
        
        current_time = time.time()
        elapsed = current_time - self.notification_send_start_time
        
        # Animated loading indicator
        center_x = WINDOW_WIDTH // 2
        center_y = WINDOW_HEIGHT // 2 - 100
        
        # Background overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(100)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # Event info
        event = self.notification_send_event
        detected_class = event.get('detected_class', 'Unknown')
        confidence = event.get('max_confidence', 0.0)
        
        # Determine status
        if self.notification_send_end_time:
            # Show success/failure
            if self.notification_sent_successfully:
                title_text = self.font_large.render("✓ Notification Sent!", True, COLORS['success'])
            else:
                title_text = self.font_large.render("✗ Failed to Send", True, COLORS['alert'])
        else:
            # Show sending status
            title_text = self.font_large.render("📤 Sending Notification...", True, COLORS['info'])
        
        title_rect = title_text.get_rect(center=(center_x, center_y - 60))
        self.screen.blit(title_text, title_rect)
        
        # Event details
        details_text = self.font_medium.render(
            f"{detected_class} ({confidence*100:.0f}%)", 
            True, COLORS['text']
        )
        details_rect = details_text.get_rect(center=(center_x, center_y - 20))
        self.screen.blit(details_text, details_rect)
        
        if not self.notification_send_end_time:
            # Animated spinner (rotating dots) - only show while sending
            spinner_radius = 20
            num_dots = 8
            for i in range(num_dots):
                angle = (elapsed * 2 + i * (2 * math.pi / num_dots)) % (2 * math.pi)
                x = center_x + int(spinner_radius * math.cos(angle))
                y = center_y + int(spinner_radius * math.sin(angle))
                
                # Fade effect
                dot_alpha = int(128 + 127 * math.sin(elapsed * 3 + i))
                dot_color = (
                    COLORS['info'][0],
                    COLORS['info'][1], 
                    COLORS['info'][2]
                )
                
                pygame.draw.circle(self.screen, dot_color, (x, y), 5)
            
            # Progress bar
            bar_width = 300
            bar_height = 8
            bar_x = center_x - bar_width // 2
            bar_y = center_y + 40
            
            # Background bar
            pygame.draw.rect(self.screen, (50, 50, 50), 
                            (bar_x, bar_y, bar_width, bar_height))
            
            # Progress (pulsing)
            progress = 0.5 + 0.5 * math.sin(elapsed * 2)
            progress_width = int(bar_width * progress)
            pygame.draw.rect(self.screen, COLORS['info'], 
                            (bar_x, bar_y, progress_width, bar_height))
            
    def _handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_f:
                    # Toggle fullscreen
                    global FULLSCREEN
                    FULLSCREEN = not FULLSCREEN
                    if FULLSCREEN:
                        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.FULLSCREEN)
                    else:
                        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                        
    def _update_stats(self):
        """Update statistics"""
        current_time = time.time()
        
        # Update FPS
        if current_time - self.last_fps_update >= 1.0:
            self.stats['fps'] = self.fps_frames
            self.fps_frames = 0
            self.last_fps_update = current_time
                        
    def run(self):
        """Run main application loop"""
        self.running = True
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_frame_loop, daemon=True)
        self.processing_thread.start()
        
        print("✓ Application started")
        print("Press ESC to exit, F to toggle fullscreen")
        
        try:
            while self.running:
                self._handle_events()
                
                # Clear screen
                self.screen.fill(COLORS['background'])
                
                # Update stats
                self._update_stats()
                
                # Draw frame
                self._draw_frame()
                
                # Draw overlays
                self._draw_stats()
                self._draw_notifications()
                self._draw_sending_indicator()
                
                # Update display
                pygame.display.flip()
                
                # Control FPS
                self.clock.tick(FPS)
                
        finally:
            self.running = False
            self.cap.release()
            pygame.quit()
            print("Application closed")
