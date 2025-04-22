# chat_inspector.py (Telethon version)
import yaml
from telethon import TelegramClient
from config.config_loader import load_config

async def inspect_chats():
    config = load_config()
    client = TelegramClient(config["session_name"], config["api_id"], config["api_hash"])
    await client.start(config["phone_number"])

    result = []
    print("\n📋 Your joined chats:\n")

    async for dialog in client.iter_dialogs():
        chat = dialog.entity
        chat_type = type(chat).__name__
        entry = {
            "title": getattr(chat, "title", "Private Chat"),
            "username": f"@{getattr(chat, 'username', '')}" if getattr(chat, 'username', None) else None,
            "chat_id": chat.id,
            "type": chat_type
        }
        result.append(entry)

        print(f"[{chat_type}] {entry['title']}")
        print(f"   chat_id: {chat.id}")
        if entry['username']:
            print(f"   username: {entry['username']}")
        print()

    with open("chats.yaml", "w") as f:
        yaml.dump(result, f, allow_unicode=True)
    print("✅ Exported to chats.yaml")

if __name__ == "__main__":
    import asyncio
    asyncio.run(inspect_chats())
