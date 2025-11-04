# test_trade_button_in_thread.py
import yaml
import asyncio
from telethon import TelegramClient, Button

# 1) Загрузим конфиг
cfg = yaml.safe_load(open("config/config.yaml", encoding="utf-8"))
api_id   = cfg["api_id"]
api_hash = cfg["api_hash"]
session  = cfg.get("session_name", "route_bot.session")

# 2) Укажите ID группы и ID стартового сообщения темы (thread_id)
TARGET_CHAT_ID = -1002447090280   # ← ваша форум-группа
THREAD_ID      = 1066             # ← thread_id той темы, где вы хотите проверить

async def main():
    client = TelegramClient(session, api_id, api_hash)
    await client.start()

    # Кнопка из вашего кода
    btn = [[Button.url("🟢 Торговать", "https://t.me/hyperdex_bot?start=placeholder")]]

    # Отправляем тестовое сообщение в ту же ветку
    await client.send_message(
        TARGET_CHAT_ID,
        "🔍 Тест кнопки в теме",
        reply_to=THREAD_ID,
        buttons=btn
    )
    print("✅ Тестовое сообщение отправлено в тему. Проверьте кнопку.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
