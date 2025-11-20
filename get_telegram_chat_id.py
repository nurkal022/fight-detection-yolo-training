#!/usr/bin/env python3
"""
Script to get Telegram channel/group chat ID for bot notifications.

Usage:
1. Add bot to your channel/group as administrator
2. Send a message to the channel/group
3. Run this script with your bot token
4. Copy the chat_id and add it to app/config.py
"""

import sys
import requests

def get_chat_id(bot_token):
    """Get chat ID from bot updates."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ Error: {data.get('description', 'Unknown error')}")
            return None
        
        updates = data.get('result', [])
        
        if not updates:
            print("⚠️  No updates found.")
            print("\n📝 Instructions:")
            print("1. Add bot to your channel/group as administrator")
            print("2. Send a message to the channel/group")
            print("3. Run this script again")
            return None
        
        print("📋 Found chats:\n")
        chat_ids = set()
        
        for update in updates:
            if 'message' in update:
                chat = update['message']['chat']
                chat_id = chat['id']
                chat_type = chat['type']
                chat_title = chat.get('title') or chat.get('username') or chat.get('first_name', 'Unknown')
                
                if chat_id not in chat_ids:
                    chat_ids.add(chat_id)
                    print(f"  {chat_type.upper()}: {chat_title}")
                    print(f"  Chat ID: {chat_id}")
                    if chat_type == 'channel':
                        print(f"  Username: @{chat.get('username', 'N/A')}")
                    print()
        
        if chat_ids:
            print("✅ Use one of these Chat IDs in app/config.py:")
            print(f"   TELEGRAM_CHAT_ID = '{list(chat_ids)[0]}'")
            if len(chat_ids) > 1:
                print(f"\n   Or multiple: TELEGRAM_CHAT_ID = '{','.join(map(str, chat_ids))}'")
        
        return list(chat_ids)[0] if chat_ids else None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_bot(bot_token, chat_id):
    """Test sending a message to the chat."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': '✅ Бот настроен! Уведомления о детекции будут приходить сюда.',
            'parse_mode': 'HTML'
        }, timeout=10)
        
        if response.status_code == 200:
            print(f"\n✅ Тестовое сообщение отправлено в чат {chat_id}")
            return True
        else:
            print(f"\n❌ Ошибка отправки: {response.text}")
            return False
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False


if __name__ == '__main__':
    bot_token = '8237778300:AAEfUDpqzZkzfvoPtT3ukKYODpD33sxlZv4'
    
    print("=" * 60)
    print("Telegram Chat ID Finder")
    print("=" * 60)
    print(f"\nBot Token: {bot_token[:20]}...")
    print()
    
    # Get chat ID
    chat_id = get_chat_id(bot_token)
    
    # Test if chat_id provided as argument
    if len(sys.argv) > 1:
        test_chat_id = sys.argv[1]
        print(f"\n🧪 Testing chat ID: {test_chat_id}")
        test_bot(bot_token, test_chat_id)

