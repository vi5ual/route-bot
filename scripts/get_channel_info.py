# scripts/get_channel_info.py

import sys
from telethon import TelegramClient
from config.config_loader import load_config

async def main():
    if len(sys.argv) != 2:
        print("Usage: python get_channel_info.py <chat_id>")
        return

    chat_id = int(sys.argv[1])
    config = load_config()

    client = TelegramClient(
        config["session_name"],
        config["api_id"],
        config["api_hash"]
    )
    await client.start(config["phone_number"])

    try:
        entity = await client.get_entity(chat_id)
    except Exception as e:
        print(f"❌ Не удалось резолвить {chat_id}: {e}")
        return

    # У большинства каналов / супергрупп есть access_hash
    ah = getattr(entity, "access_hash", None)
    title = getattr(entity, "title", None) or getattr(entity, "username", None)
    print(f"✅ Найдено:\n"
          f"  id:            {entity.id}\n"
          f"  access_hash:   {ah}\n"
          f"  title/username:{title}")

    await client.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
