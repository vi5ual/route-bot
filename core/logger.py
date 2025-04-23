import json
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("routing_log.json")

def load_log():
    if LOG_PATH.exists():
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_log(log_data):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

def update_routing_log(keyword: str, thread_id: int):
    log_data = load_log()

    entry = log_data.get(keyword, {
        "count": 0,
        "thread_id": thread_id,
        "last_used": None
    })

    entry["count"] += 1
    entry["last_used"] = datetime.utcnow().isoformat()

    log_data[keyword] = entry
    save_log(log_data)
