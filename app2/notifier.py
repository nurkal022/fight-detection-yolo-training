"""
Notification system for standalone application
"""
import requests
import os
from config import TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class Notifier:
    """Handles notifications (Telegram)"""
    
    def __init__(self):
        """Initialize notifier"""
        self.enabled = TELEGRAM_ENABLED and bool(TELEGRAM_BOT_TOKEN) and bool(TELEGRAM_CHAT_ID)
        if not self.enabled:
            reasons = []
            if not TELEGRAM_ENABLED:
                reasons.append("TELEGRAM_ENABLED=False")
            if not TELEGRAM_BOT_TOKEN:
                reasons.append("TELEGRAM_BOT_TOKEN not set")
            if not TELEGRAM_CHAT_ID:
                reasons.append("TELEGRAM_CHAT_ID not set")
            print(f"⚠️ Telegram notifications disabled: {', '.join(reasons)}")
        
    def send_notification(self, event_data):
        """
        Send notification about detection event.
        
        Args:
            event_data: Dictionary with event information
        """
        if not self.enabled:
            return
            
        try:
            detected_class = event_data.get('detected_class', 'Unknown')
            confidence = event_data.get('max_confidence', 0.0)
            duration = event_data.get('duration', 0.0)
            detection_count = event_data.get('detection_count', 0)
            
            caption = (
                f"<b>🚨 Fight Detection Alert</b>\n"
                f"👊 Detected: <b>{detected_class}</b>\n"
                f"📊 Confidence: {int(confidence*100)}%\n"
                f"⏱ Duration: {duration:.1f}s\n"
                f"🔢 Detections: {detection_count}\n"
                f"🕐 Time: {event_data['start_time'].strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
            
            # Send text message
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            response = requests.post(url, json={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': caption,
                'parse_mode': 'HTML'
            }, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ Telegram notification sent: {detected_class}")
            else:
                print(f"✗ Telegram notification failed: {response.text}")
                
        except Exception as e:
            print(f"Error sending notification: {e}")

