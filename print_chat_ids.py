from telethon import TelegramClient, events
import yaml

# Подключаем конфиг как в main.py
with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

client = TelegramClient(
    cfg["session_name"],
    cfg["api_id"],
    cfg["api_hash"]
)

@client.on(events.NewMessage())
async def handler(event):
    print(f"🆔 chat_id = {event.chat_id} ({event.chat.title or event.chat.username or 'Private Chat'})")
    # После того, как ID получили, можешь убрать этот обработчик или закрыть скрипт.

async def main():
    await client.start(cfg["phone_number"])
    print("📡 Listening for any new message…")
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
