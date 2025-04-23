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

    # 1. Боты-сигнальщики
    routes = config.get("routes", [])
    print(f"[MAIN] Активные маршруты (боты): {len(routes)}")
    for r in routes:
        src = r["source"].get("username") or r["source"].get("chat_id")
        tid = r.get("thread_id")
        print(f"  • {src} → thread_id={tid}")
    print()

    await setup_forwarding(client, routes, mode=config.get("mode", "copy"))

    # 2. Новости
    news_cfg = config.get("news", {})
    news_source = news_cfg.get("source")
    news_target = news_cfg.get("target_chat")
    print(f"[MAIN] Источник новостей: {news_source} → группа {news_target}\n")

    await setup_router_forwarding(client, news_source, news_target)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
