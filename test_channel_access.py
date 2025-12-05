# test_channel_access.py - Проверка доступа к каналам
import asyncio
from telethon import TelegramClient
from config.config_loader import load_config

async def test_channel_access():
    """Проверяет доступ к каналам PifSignal и Signal"""
    config = load_config()
    
    client = TelegramClient(
        config["session_name"],
        config["api_id"],
        config["api_hash"]
    )
    await client.start(config["phone_number"])
    print("[TEST] Client started\n")
    
    # Тестируем каналы
    channels = [
        (-1003171748254, "PifSignal"),
        (-1003300013586, "Signal"),
    ]
    
    for chat_id, name in channels:
        print(f"\n{'='*60}")
        print(f"Testing: {name} (chat_id: {chat_id})")
        print(f"{'='*60}")
        
        try:
            entity = await client.get_entity(chat_id)
            print(f"✅ Successfully accessed!")
            print(f"   ID: {entity.id}")
            print(f"   Title: {getattr(entity, 'title', 'N/A')}")
            print(f"   Type: {type(entity).__name__}")
            
            # Проверяем access_hash
            access_hash = getattr(entity, 'access_hash', None)
            if access_hash:
                print(f"   Access Hash: {access_hash}")
            
            # Пробуем получить последние сообщения
            try:
                messages = await client.get_messages(entity, limit=3)
                print(f"   ✅ Can read messages: {len(messages)} messages retrieved")
                if messages:
                    print(f"   Latest message preview: {messages[0].message[:50] if messages[0].message else '(no text)'}")
            except Exception as e:
                print(f"   ⚠️ Cannot read messages: {e}")
            
            # Пробуем отправить тестовое сообщение (если это группа)
            if hasattr(entity, 'broadcast') and not entity.broadcast:
                try:
                    test_msg = await client.send_message(entity, "🧪 Test message from route-bot")
                    print(f"   ✅ Can send messages (test message ID: {test_msg.id})")
                    # Удаляем тестовое сообщение
                    await client.delete_messages(entity, [test_msg])
                    print(f"   ✅ Test message deleted")
                except Exception as e:
                    print(f"   ⚠️ Cannot send messages: {e}")
            
        except Exception as e:
            print(f"❌ Failed to access channel!")
            print(f"   Error: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            
            # Пробуем получить access_hash через другой способ
            print(f"\n   Trying alternative method...")
            try:
                # Пробуем найти в диалогах
                async for dialog in client.iter_dialogs():
                    if dialog.entity.id == chat_id or abs(dialog.entity.id) == abs(chat_id):
                        print(f"   ✅ Found in dialogs!")
                        print(f"      Dialog ID: {dialog.entity.id}")
                        print(f"      Title: {getattr(dialog.entity, 'title', 'N/A')}")
                        access_hash = getattr(dialog.entity, 'access_hash', None)
                        if access_hash:
                            print(f"      Access Hash: {access_hash}")
                        break
                else:
                    print(f"   ⚠️ Not found in dialogs")
            except Exception as e2:
                print(f"   ⚠️ Alternative method failed: {e2}")
    
    print(f"\n{'='*60}")
    print("Test completed!")
    print(f"{'='*60}\n")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_channel_access())








