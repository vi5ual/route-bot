from telethon import events, TelegramClient
from telethon.tl.custom.message import Message
from core.router import load_filters, detect_topic

filters = load_filters()

def get_source_key(route):
    """Возвращает username или chat_id источника."""
    if isinstance(route["source"], dict):
        return route["source"].get("chat_id") or route["source"].get("username")
    return route["source"]

async def setup_forwarding(client: TelegramClient, routes: list, mode: str = "copy"):
    mapping = {}
    for route in routes:
        key = str(get_source_key(route))
        mapping.setdefault(key, []).append({
            "target_chat": route["target_chat"],
            "thread_id": route.get("thread_id", None)
        })

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

                # Автоматическая маршрутизация, если не задано явно
                if thread_id is None:
                    auto_thread_id, reason = detect_topic(event.raw_text or "", filters)
                    thread_id = auto_thread_id
                    print(f"[ROUTER] Автоопределение темы: '{reason}' → thread_id={thread_id}")

                if mode == "forward":
                    await client.forward_messages(entity, event.message)
                    print(f"[FORWARD] {src} → {target}")
                else:
                    if thread_id is not None:
                        await client.send_message(
                            entity=entity,
                            message=event.raw_text or "",
                            formatting_entities=event.message.entities,
                            file=event.media if event.media else None,
                            link_preview=False,
                            reply_to=thread_id
                        )
                        print(f"[COPY] {src} → {target} (thread {thread_id})")
                    else:
                        print(f"[SKIP] {src} → {target}: Не удалось определить thread_id")

            except Exception as e:
                print(f"[ERROR] {src} → {target} (thread {thread_id}) failed: {e}")
