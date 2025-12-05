# core/forwarder.py - Способ 3: Инлайн кнопки

import re
import yaml
import os
import tempfile
print("LOADED forwarder.py")

from telethon import events, TelegramClient, Button
from telethon.tl.types import InputPeerChannel, MessageMediaPhoto, MessageMediaDocument
from core.router import _best_match, _load_rules

cfg = yaml.safe_load(open("config/config.yaml", encoding="utf-8"))
FEATURE_FLAGS = cfg.get("features", {})

EXCLUDE_THREAD_IDS = set()
news_config = cfg.get("news", {})
if news_config:
    exclude_tid = news_config.get("thread_id")
    if exclude_tid:
        EXCLUDE_THREAD_IDS.add(exclude_tid)

_, RULES = _load_rules()

def _contains_profit_loss(text):
    """Проверяет, содержит ли сообщение информацию о прибыли/убытке (закрытые сделки)"""
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Сначала проверяем ключевые фразы для закрытых сделок - они имеют приоритет
    # Ключевые фразы для закрытых сделок с прибылью/убытком
    profit_loss_keywords = [
        "сделка закрыта в плюс",
        "сделка закрыта в минус",
        "закрыта в плюс",
        "закрыта в минус",
    ]
    
    # Проверяем наличие ключевых фраз о закрытых сделках
    for keyword in profit_loss_keywords:
        if keyword in text_lower:
            return True
    
    # Проверяем паттерн "PNL: +XX.XX%" или "PNL: -XX.XX%" - используется в professionallarge_bot
    # Это явный признак закрытой сделки с результатом
    if re.search(r'pnl\s*:\s*[+\-]\s*\d+\.?\d*\s*%', text_lower, re.IGNORECASE):
        return True
    
    # Если нет явных признаков закрытой сделки, проверяем исключения
    # Исключаем сообщения с настройками/конфигурацией/ошибками
    exclude_keywords = [
        "настройки",
        "settings",
        "auto-trade",
        "соединение установлено",
        "connection established",
        "кредитное плечо",
        "leverage",
        "max сигналов",
        "max signals",
        "max открытых сделок",
        "max open trades",
        "тип трейда",
        "trade type",
        "breakeven",
        "trailing stop",
        "api:",
        "входной ордер",
        "не исполнен",
        "не исполнен воврем",
        "order not executed",
    ]
    
    # Если сообщение содержит слова из исключений, это не закрытая сделка
    for exclude_kw in exclude_keywords:
        if exclude_kw in text_lower:
            return False
    
    # Проверяем паттерны результата сделки: "Take profit + % 12.94" или "Stop loss - % 19.15"
    # Важно: должно быть сочетание "take profit" или "stop loss" с конкретным результатом сделки
    if re.search(r'take\s+profit\s*[+\-]\s*%\s*\d+', text_lower, re.IGNORECASE):
        return True
    if re.search(r'stop\s+loss\s*[+\-]\s*%\s*\d+', text_lower, re.IGNORECASE):
        return True
    
    # Проверяем наличие "Account Balance" вместе с процентами - это признак закрытой сделки
    if "account balance" in text_lower and re.search(r'[+\-]\s*%\s*\d+\.?\d*', text):
        return True
    
    # Проверяем паттерны "+ %" / "- %" с числами, но только если это не настройки
    # Добавляем проверку, что это выглядит как результат сделки, а не настройка
    if re.search(r'[+\-]\s*%\s*\d+\.?\d*', text) and "закрыта" in text_lower:
        return True
    
    return False

def _resolve_input_peer(src):
    if isinstance(src, dict):
        cid = src.get("chat_id")
        ah = src.get("access_hash")
        if ah is not None:
            return InputPeerChannel(channel_id=abs(cid), access_hash=ah)
        if src.get("username"):
            return src["username"]
        # Возвращаем chat_id, если нет username и access_hash
        # TelegramClient.get_entity() может работать с числовым ID
        return cid
    return src

async def setup_forwarding(client: TelegramClient, routes, mode="copy"):
    src_entities = {}
    tgt_entities = {}
    for r in routes:
        raw = r["source"]
        key = str(raw)
        if key not in src_entities:
            try:
                peer = _resolve_input_peer(raw)
                print(f"[FORWARDER] Resolving source: {raw} → {peer}")
                src_entities[key] = await client.get_entity(peer)
                print(f"[FORWARDER] ✅ Source resolved: {src_entities[key].id} ({getattr(src_entities[key], 'title', 'N/A')})")
            except Exception as e:
                print(f"[FORWARDER][ERR] Failed to resolve source {raw}: {e}")
                continue
        tgt = r["target_chat"]
        if tgt not in tgt_entities:
            try:
                print(f"[FORWARDER] Resolving target: {tgt}")
                tgt_entities[tgt] = await client.get_entity(tgt)
                print(f"[FORWARDER] ✅ Target resolved: {tgt_entities[tgt].id} ({getattr(tgt_entities[tgt], 'title', 'N/A')})")
            except Exception as e:
                print(f"[FORWARDER][ERR] Failed to resolve target {tgt}: {e}")
                continue

    routes_by_chat = {}
    for r in routes:
        key = str(r["source"])
        if key not in src_entities:
            print(f"[FORWARDER] ⚠️ Skipping route: source {key} not resolved")
            continue
        ent = src_entities[key]
        # Регистрируем маршрут для обоих вариантов ID (положительный и отрицательный)
        # ev.chat_id может быть -1003171748254, а entity.id = 3171748254
        routes_by_chat.setdefault(ent.id, []).append(r)
        # Также регистрируем для отрицательного формата (если это канал/супергруппа)
        if ent.id > 0:
            negative_id = -1000000000000 - ent.id
            routes_by_chat.setdefault(negative_id, []).append(r)
            print(f"[FORWARDER] 📍 Route registered: {ent.id} and {negative_id} → {r['target_chat']} (thread_id={r.get('thread_id')})")
        else:
            print(f"[FORWARDER] 📍 Route registered: {ent.id} → {r['target_chat']} (thread_id={r.get('thread_id')})")

    # Получаем все chat_id для подписки на события
    all_chat_ids = list(routes_by_chat.keys())
    print(f"[FORWARDER] 📡 Subscribing to {len(all_chat_ids)} chat(s): {all_chat_ids}")

    # Message ID mapping: (source_chat_id, source_msg_id, target_chat_id, thread_id) -> target_msg_id
    # This allows us to preserve reply structure when forwarding
    message_id_map = {}
    
    @client.on(events.NewMessage(chats=all_chat_ids))
    async def handler(ev):
        chat_id = ev.chat_id
        print(f"[FORWARDER] 📨 New message from chat_id: {chat_id}")
        
        # Ищем маршрут для этого chat_id
        route_list = routes_by_chat.get(chat_id, [])
        
        if not route_list:
            print(f"[FORWARDER] ⚠️ No route found for chat_id: {chat_id}")
            print(f"[FORWARDER] 📋 Available routes for chat_ids: {list(routes_by_chat.keys())}")
            return
        
        for r in route_list:
            # Проверяем, нужна ли фильтрация для этого маршрута
            require_profit_loss = r.get("filter_profit_loss", False)

            if require_profit_loss:
                text = ev.raw_text or ""
                if not _contains_profit_loss(text):
                    print(f"[FORWARDER] Skipped (no profit/loss): {chat_id} → {r['target_chat']}")
                    continue

            tgt_ent = tgt_entities[r["target_chat"]]
            tid = r.get("thread_id")
            if tid is None:
                tid, _ = _best_match(ev.raw_text or "", RULES)

            # Preserve reply structure
            reply_to = tid  # Default to thread_id if no reply
            reply_to_top_id = None

            # Check if the original message is a reply
            if ev.message.reply_to:
                source_reply_msg_id = ev.message.reply_to.reply_to_msg_id
                # Look up the corresponding target message ID
                map_key = (chat_id, source_reply_msg_id, r["target_chat"], tid)
                target_reply_msg_id = message_id_map.get(map_key)

                if target_reply_msg_id:
                    reply_to = target_reply_msg_id
                    print(f"[FORWARDER] 💬 Preserving reply: source_msg {source_reply_msg_id} → target_msg {target_reply_msg_id}")
                else:
                    print(f"[FORWARDER] ⚠️ Reply target not found in map: source_msg {source_reply_msg_id}")

                # Preserve forum topic thread if present
                if hasattr(ev.message.reply_to, 'reply_to_top_id') and ev.message.reply_to.reply_to_top_id:
                    reply_to_top_id = ev.message.reply_to.reply_to_top_id

            try:
                TRADE_LINK = (
                    "https://t.me/hyperdx_bot?start=real_trade"
                    if FEATURE_FLAGS.get("enable_trade_button")
                    else "https://t.me/iv?url=about:blank"
                )

                # Отправляем оригинальное сообщение с инлайн кнопкой
                button_text = "🟢 Торговать"
                if not FEATURE_FLAGS.get("enable_trade_button"):
                    button_text += " (в разработке)"

                buttons = [Button.url(button_text, TRADE_LINK)]

                # Проверяем наличие медиафайла и его тип
                has_media = ev.message.media is not None
                media_type = None
                media_file_path = None
                
                if has_media:
                    media_type = type(ev.message.media).__name__
                    
                    # Пересылаем только изображения (фото), игнорируем остальные типы медиа
                    if isinstance(ev.message.media, MessageMediaPhoto):
                        print(f"[FORWARDER] 📷 Message contains photo")
                    elif isinstance(ev.message.media, MessageMediaDocument):
                        # Проверяем, является ли документ изображением
                        doc = ev.message.media.document
                        if doc:
                            # Получаем mime_type документа
                            mime_type = getattr(doc, 'mime_type', '')
                            if mime_type and mime_type.startswith('image/'):
                                print(f"[FORWARDER] 📷 Message contains image document")
                            else:
                                # Это не изображение (голосовое, видео и т.д.) - пропускаем медиа
                                print(f"[FORWARDER] ⏭️ Skipping non-image media: {mime_type or 'unknown'}")
                                has_media = False
                    else:
                        # Другой тип медиа - пропускаем
                        print(f"[FORWARDER] ⏭️ Skipping unsupported media type: {media_type}")
                        has_media = False
                
                # Если есть медиа (только изображения), скачиваем его
                if has_media:
                    try:
                        # Определяем расширение файла на основе типа медиа
                        file_ext = '.jpg'  # По умолчанию jpg
                        
                        # Создаем временный файл
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                            tmp_path = tmp_file.name
                        
                        # Скачиваем медиафайл во временный файл
                        downloaded_path = await client.download_media(ev.message.media, file=tmp_path)
                        media_file_path = downloaded_path or tmp_path
                        file_size = os.path.getsize(media_file_path) if os.path.exists(media_file_path) else 0
                        print(f"[FORWARDER] 📥 Downloaded media: {file_size} bytes -> {media_file_path}")
                        
                    except Exception as media_err:
                        print(f"[FORWARDER] ⚠️ Failed to download media: {media_err}")
                        import traceback
                        print(f"[FORWARDER] Traceback: {traceback.format_exc()}")
                        has_media = False
                        media_file_path = None

                # Отправляем сообщение
                try:
                    sent_msg = None
                    if has_media and media_file_path:
                        # Отправляем с медиафайлом (изображение)
                        sent_msg = await client.send_file(
                            tgt_ent,
                            media_file_path,
                            caption=ev.message.message or "",  # Текст под изображением
                            formatting_entities=ev.message.entities,  # Сохраняем форматирование
                            reply_to=reply_to,
                            buttons=buttons
                        )
                        print(f"[FORWARDER] ✅ Forwarded with image: {chat_id} → {r['target_chat']} (msg_id: {sent_msg.id})")

                        # Удаляем временный файл после отправки
                        try:
                            if os.path.exists(media_file_path):
                                os.unlink(media_file_path)
                        except:
                            pass
                    else:
                        # Отправляем только текст без медиа
                        sent_msg = await client.send_message(
                            tgt_ent,
                            message=ev.message.message or "",
                            formatting_entities=ev.message.entities,
                            reply_to=reply_to,
                            buttons=buttons,
                            link_preview=False
                        )
                        print(f"[FORWARDER] ✅ Forwarded text only: {chat_id} → {r['target_chat']} (msg_id: {sent_msg.id})")

                    # Store the message ID mapping for future replies
                    if sent_msg:
                        map_key = (chat_id, ev.message.id, r["target_chat"], tid)
                        message_id_map[map_key] = sent_msg.id
                        print(f"[FORWARDER] 📝 Stored mapping: source_msg {ev.message.id} → target_msg {sent_msg.id}")
                        
                except Exception as send_err:
                    # Удаляем временный файл при ошибке
                    if media_file_path and os.path.exists(media_file_path):
                        try:
                            os.unlink(media_file_path)
                        except:
                            pass
                    raise send_err
                
            except Exception as e:
                import traceback
                print(f"[FORWARDER][ERR] Failed to forward from {chat_id} to {r['target_chat']}: {e}")
                print(f"[FORWARDER][ERR] Traceback: {traceback.format_exc()}")

    _ = handler
