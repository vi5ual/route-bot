# core/router.py
import yaml, re
from telethon import events
from telethon.tl.types import InputPeerChannel
from core.logger import update_routing_log

def _load_rules(path="config/filters.yaml"):
    data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    bl  = data.get("blacklist", [])
    raw = data.get("filters", {})

    rules = []
    if isinstance(raw, dict):
        for kw, tid in raw.items():
            rules.append({"keyword": kw, "thread_id": tid, "priority": 100, "is_tag": kw.startswith("#")})
    else:
        for e in raw:
            rules.append({
                "keyword":   e["keyword"],
                "thread_id": e["thread_id"],
                "priority":  e.get("priority", 100),
                "is_tag":    e["keyword"].startswith("#")
            })
    return bl, rules

def _best_match(text: str, rules: list):
    text = text.lower()
    hits = []
    for r in rules:
        kw = r["keyword"].lower()
        if r["is_tag"]:
            idx = text.find(kw)
            if idx != -1:
                hits.append((r, idx))
        else:
            # На ключи с символами (например, '(анонс)') \b не срабатывает,
            # поэтому просто ищем подстроку:
            idx = text.find(kw)
            if idx != -1:
                hits.append((r, idx))
    if not hits:
        return None, None
    best, _ = min(
        hits,
        key=lambda p: (
            0 if p[0]["is_tag"] else 1,
            -p[0]["priority"],
            p[1],
            -len(p[0]["keyword"])
        )
    )
    return best["thread_id"], best["keyword"]

def _resolve_input_peer(src):
    if isinstance(src, dict):
        cid = src.get("chat_id")
        ah  = src.get("access_hash")
        if ah is not None:
            return InputPeerChannel(channel_id=abs(cid), access_hash=ah)
        if src.get("username"):
            return src["username"]
        return cid
    return src

async def setup_router_forwarding(client, news_src, target_group):
    bl, rules = _load_rules()

    peer_src = await client.get_entity(_resolve_input_peer(news_src))
    peer_tgt = await client.get_entity(target_group)

    print(f"[ROUTER] старт для {news_src} → {target_group}, правил: {len(rules)}")

    @client.on(events.NewMessage(chats=[peer_src.id]))
    async def handler(ev):
        txt = ev.raw_text or ""
        print("RAW_TEXT:", repr(txt))  # ⬅️ добавили сюда
        low = txt.lower()

        for bad in bl:
            if bad.lower() in low:
                print(f"[ROUTER] blacklisted '{bad}'")
                return

        tid, kw = _best_match(txt, rules)
        if not tid:
            print(f"[ROUTER] no match …{txt[:30]}")
            return

        update_routing_log(kw, tid)

        try:
            await client.send_message(
                peer_tgt,
                message=txt,
                formatting_entities=ev.message.entities,
                file=ev.media or None,
                link_preview=False,
                reply_to=tid
            )
            print(f"[ROUTER] ok → thread {tid} by '{kw}'")
        except Exception as e:
            print(f"[ROUTER][ERR] {e}")

    _ = handler
