# core/forwarder.py - Способ 3: Инлайн кнопки

import re
import yaml
print("LOADED forwarder.py")

from telethon import events, TelegramClient, Button
from telethon.tl.types import InputPeerChannel
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
        return cid
    return src

async def setup_forwarding(client: TelegramClient, routes, mode="copy"):
    src_entities = {}
    tgt_entities = {}
    for r in routes:
        raw = r["source"]
        key = str(raw)
        if key not in src_entities:
            peer = _resolve_input_peer(raw)
            src_entities[key] = await client.get_entity(peer)
        tgt = r["target_chat"]
        if tgt not in tgt_entities:
            tgt_entities[tgt] = await client.get_entity(tgt)

    routes_by_chat = {}
    for r in routes:
        ent = src_entities[str(r["source"])]
        routes_by_chat.setdefault(ent.id, []).append(r)

    @client.on(events.NewMessage(chats=list(routes_by_chat.keys())))
    async def handler(ev):
        chat_id = ev.chat_id
        
        for r in routes_by_chat.get(chat_id, []):
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

                await client.send_message(
                    tgt_ent,
                    ev.message,  # Сохраняем оригинальное форматирование
                    reply_to=tid,
                    file=ev.media or None,
                    buttons=buttons
                )

                print(f"[FORWARDER] Inline button: {chat_id} → {r['target_chat']}")
                
            except Exception as e:
                print(f"[FORWARDER][ERR] {e}")

    _ = handler
