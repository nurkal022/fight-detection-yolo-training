import requests
from flask import current_app
from app.utils.logger import log_system


class TelegramNotifier:
    """Simple Telegram notifications helper."""

    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        cfg = current_app.config if current_app else {}
        self.enabled = (cfg.get('TELEGRAM_ENABLED', False) if cfg else False)
        self.bot_token = bot_token or (cfg.get('TELEGRAM_BOT_TOKEN') if cfg else None)
        self.chat_id = chat_id or (cfg.get('TELEGRAM_CHAT_ID') if cfg else None)

    def is_ready(self) -> bool:
        return bool(self.enabled and self.bot_token and self.chat_id)

    def send_message(self, text: str, chat_id: str | None = None) -> bool:
        """Send message to chat_id or default chat_id."""
        if not self.enabled or not self.bot_token:
            log_system('WARNING', 'Telegram not configured or disabled', 'telegram')
            return False
        
        target_chat_id = chat_id or self.chat_id
        if not target_chat_id:
            log_system('WARNING', 'No chat_id provided', 'telegram')
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            resp = requests.post(url, json={
                'chat_id': target_chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }, timeout=10)
            if resp.status_code != 200:
                log_system('ERROR', f'Telegram send_message failed: {resp.text}', 'telegram')
                return False
            return True
        except Exception as e:
            log_system('ERROR', f'Telegram send_message exception: {str(e)}', 'telegram')
            return False
    
    def send_message_to_multiple(self, text: str, chat_ids: list) -> dict:
        """Send message to multiple chat_ids. Returns dict with results."""
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        if not self.enabled or not self.bot_token:
            log_system('WARNING', 'Telegram not configured or disabled', 'telegram')
            return results
        
        for chat_id in chat_ids:
            if self.send_message(text, chat_id):
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(chat_id)
        
        return results

    def send_photo(self, photo_path: str, caption: str | None = None) -> bool:
        if not self.is_ready():
            log_system('WARNING', 'Telegram not configured or disabled', 'telegram')
            return False
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            with open(photo_path, 'rb') as f:
                files = {'photo': f}
                data = {'chat_id': self.chat_id}
                if caption:
                    data['caption'] = caption
                    data['parse_mode'] = 'HTML'
                resp = requests.post(url, data=data, files=files, timeout=15)
            if resp.status_code != 200:
                log_system('ERROR', f'Telegram send_photo failed: {resp.text}', 'telegram')
                return False
            return True
        except Exception as e:
            log_system('ERROR', f'Telegram send_photo exception: {str(e)}', 'telegram')
            return False

    def send_photo_to_chat(self, photo_path: str, chat_id: str, caption: str | None = None) -> bool:
        """Send photo to specific chat_id."""
        if not self.enabled or not self.bot_token:
            log_system('WARNING', 'Telegram not configured or disabled', 'telegram')
            return False
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            with open(photo_path, 'rb') as f:
                files = {'photo': f}
                data = {'chat_id': chat_id}
                if caption:
                    data['caption'] = caption
                    data['parse_mode'] = 'HTML'
                resp = requests.post(url, data=data, files=files, timeout=15)
            if resp.status_code != 200:
                log_system('ERROR', f'Telegram send_photo to {chat_id} failed: {resp.text}', 'telegram')
                return False
            return True
        except Exception as e:
            log_system('ERROR', f'Telegram send_photo to {chat_id} exception: {str(e)}', 'telegram')
            return False

    def send_photo_to_multiple(self, photo_path: str, chat_ids: list, caption: str | None = None) -> dict:
        """Send photo to multiple chat_ids. Returns dict with results."""
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        if not self.enabled or not self.bot_token:
            log_system('WARNING', 'Telegram not configured or disabled', 'telegram')
            return results
        
        for chat_id in chat_ids:
            if self.send_photo_to_chat(photo_path, chat_id, caption):
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(chat_id)
        
        return results


