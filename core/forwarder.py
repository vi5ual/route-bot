from telethon import events, TelegramClient

def get_source_key(route):
    """Return the identifier used for filters: username or chat_id."""
    if route["source"].get("chat_id") is not None:
        return route["source"]["chat_id"]
    return route["source"]["username"]

async def setup_forwarding(client: TelegramClient, routes: list):
    """
    Настраивает пересылку сообщений от заданных источников в темы целевого чата.
    """
    # source → [(target_chat, thread_id)]
    mapping = {}
    for route in routes:
        key = get_source_key(route)
        mapping.setdefault(str(key), []).append(
            (route["target_chat"], route["thread_id"])
        )

    # Получаем список чатов-источников
    all_sources = [int(k) if str(k).isdigit() else k for k in mapping.keys()]

    @client.on(events.NewMessage(chats=all_sources))
    async def handler(event):
        src = str(event.chat_id or event.chat.username)
        text = event.raw_text or ""

        if src not in mapping:
            print(f"[SKIP] Unknown source: {src}")
            return

        for target_chat, thread_id in mapping[src]:
            try:
                # 🔥 Получаем entity через get_entity
                entity = await client.get_entity(target_chat)
                await client.send_message(
                    entity=entity,
                    message=text,
                    reply_to=thread_id  # для отправки в тему
                )
                print(f"[FORWARD] {src} → {target_chat} (thread {thread_id}): {text[:50]!r}")
            except Exception as e:
                print(f"[ERROR] Sending from {src} to {target_chat} (thread {thread_id}) failed: {e}")
