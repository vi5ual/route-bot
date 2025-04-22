import yaml
import asyncio
from telethon import TelegramClient
from config.config_loader import load_config
from collections import defaultdict

async def list_threads():
    config = load_config()

    client = TelegramClient(config["session_name"], config["api_id"], config["api_hash"])
    await client.start(config["phone_number"])
    print("[THREADS] Client started")

    group_ref = config["group_with_threads"]
    group_entity = None

    async for dialog in client.iter_dialogs():
        chat = dialog.entity
        if str(chat.id) == str(group_ref):
            group_entity = chat
            break

    if not group_entity:
        print(f"❌ Group '{group_ref}' not found.")
        return

    print(f"\n📋 Topics in group: {group_entity.title} (id: {group_entity.id})\n")

    messages = await client.get_messages(group_entity, limit=100)

    seen = set()
    topics = {}
    for msg in messages:
        thread_id = getattr(msg, "thread_id", None) or getattr(msg, "message_thread_id", None)
        if thread_id and thread_id not in seen:
            seen.add(thread_id)
            preview = msg.message.strip()[:80] if msg.message else "(no content)"
            print(f"🧵 thread_id: {thread_id:<5} | preview: {preview}")
            topics[preview] = thread_id

    if not topics:
        print("⚠️ No topics with messages found. Try sending messages manually into each topic.")
    else:
        with open("threads.yaml", "w", encoding="utf-8") as f:
            yaml.dump(topics, f, allow_unicode=True)
        print("\n✅ Saved to threads.yaml")

if __name__ == "__main__":
    asyncio.run(list_threads())
