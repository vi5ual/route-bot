# core/router.py
import yaml
import re
from telethon import events
from telethon.tl.custom.message import Message
from core.logger import update_routing_log

def load_filters(path="config/filters.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("filters", {})

def detect_topic(message_text: str, filters: dict):
    text = (message_text or "").lower()
    for keyword, thread_id in filters.items():
        if re.search(re.escape(keyword.lower()), text):
            return thread_id, keyword
    return None, None

async def setup_router_forwarding(client, news_source, target_group):
    """
    Подписывается на новости от news_source и
    отправляет их в темы target_group по ключам из filters.yaml,
    а также обновляет routing_log.json.
    """
    filters = load_filters()

    print(f"[ROUTER] Запуск новостного маршрутизатора для {news_source}")

    @client.on(events.NewMessage(chats=[news_source]))
    async def handler(event: Message):
        try:
            auto_thread_id, reason = detect_topic(event.raw_text, filters)
            if auto_thread_id:
                # Логируем в статистику
                update_routing_log(reason, auto_thread_id)

                # Отправляем в нужную тему
                entity = await client.get_entity(target_group)
                await client.send_message(
                    entity=entity,
                    message=event.raw_text or "",
                    formatting_entities=event.message.entities,
                    file=event.media if event.media else None,
                    link_preview=False,
                    reply_to=auto_thread_id
                )
                print(f"[NEWS] {news_source} → {target_group} (thread {auto_thread_id}) по ключу '{reason}'")
            else:
                print(f"[NEWS] Пропущено: нет совпадений ({event.raw_text[:30]}...)")

        except Exception as e:
            print(f"[NEWS][ERROR] {e}")
