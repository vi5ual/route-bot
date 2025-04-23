from telethon import events, TelegramClient
from telethon.tl.custom.message import Message

def get_source_key(route):
    """Возвращает username или chat_id источника."""
    if isinstance(route["source"], dict):
        return route["source"].get("chat_id") or route["source"].get("username")
    return route["source"]

async def setup_forwarding(client: TelegramClient, routes: list, mode: str = "copy"):
    """
    Настраивает пересылку сообщений от источников в заданные темы.
    mode: "copy" или "forward"
    """
    mapping = {}
    for route in routes:
        key = str(get_source_key(route))
        mapping.setdefault(key, []).append({
            "target_chat": route["target_chat"],
            "thread_id": route.get("thread_id", None)
        })

    # Источники для фильтрации событий
    all_sources = [int(k) if str(k).isdigit() else k for k in mapping.keys()]

    @client.on(events.NewMessage(chats=all_sources))
    async def handler(event: Message):
        src = str(event.chat_id or event.chat.username)
        if src not in mapping:
            return

        for destination in mapping[src]:
            target = destination["target_chat"]
            thread_id = destination.get("thread_id")

            try:
                entity = await client.get_entity(target)

                if mode == "forward":
                    # Пересылка как оригинал, но без thread_id (Telegram API не поддерживает)
                    await client.forward_messages(entity, event.message)
                    print(f"[FORWARD] {src} → {target}")
                else:
                    # Режим копирования с сохранением форматирования и медиа
                    await client.send_message(
                        entity=entity,
                        message=event.raw_text or "",
                        formatting_entities=event.message.entities,
                        file=event.media if event.media else None,
                        link_preview=False,
                        reply_to=thread_id
                    )
                    print(f"[COPY] {src} → {target} (thread {thread_id})")

            except Exception as e:
                print(f"[ERROR] {src} → {target} (thread {thread_id}) failed: {e}")
