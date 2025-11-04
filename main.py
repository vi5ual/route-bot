# main.py
import asyncio
from telethon import TelegramClient
from config.config_loader import load_config
from core.forwarder import setup_forwarding
from core.router import setup_router_forwarding

async def main():
    config = load_config()

    client = TelegramClient(
        config["session_name"],
        config["api_id"],
        config["api_hash"]
    )
    await client.start(config["phone_number"])
    print("[TELEGRAM] Client started\n")

    # 1) Сигнальные боты
    routes = config.get("routes", [])
    print(f"[MAIN] Активные маршруты (боты): {len(routes)}")
    for r in routes:
        src = r["source"]
        if isinstance(src, dict):
            src_name = src.get("username") or src.get("chat_id")
        else:
            src_name = src
        print(f"  • {src_name} → thread_id={r.get('thread_id')}")
    print()
    await setup_forwarding(client, routes, mode=config.get("mode", "copy"))

    # 2) Новостной канал
    news = config.get("news", {})
    src = news.get("source")
    tgt = news.get("target_chat")
    print(f"[MAIN] Источник новостей: {src} → группа {tgt}\n")
    await setup_router_forwarding(client, src, tgt)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
