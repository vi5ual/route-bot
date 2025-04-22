import asyncio
from telethon import TelegramClient
from config.config_loader import load_config
from core.forwarder import setup_forwarding

async def main():
    config = load_config()

    client = TelegramClient(
        config["session_name"],
        config["api_id"],
        config["api_hash"]
    )

    await client.start(config["phone_number"])
    print("[TELEGRAM] Client started")

    # Никаких join'ов — только запуск пересылки
    await setup_forwarding(client, config["routes"])
    print(f"[MAIN] Listening with {len(config['routes'])} routes...")

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
