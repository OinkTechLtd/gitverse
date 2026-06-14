import json
import os
from datetime import datetime, timezone
from utils import fetch, parse_ctc_now, parse_1tv_now

M3U_SOURCES = [
    "https://raw.githubusercontent.com/oinktechllc/livem3u/main/playlist.m3u",
    "https://raw.githubusercontent.com/oinktechltd/rulive/master/playlist.m3u",
]

# Пример сопоставления каналов — можно расширять
CHANNEL_MAP = {
    "CTC": {
        "url": "https://www.ctc.ru/program/",
        "parser": parse_ctc_now,
        "stream_prefix": "https://live.ctc.ru",
    },
    "1TV": {
        "url": "https://www.1tv.ru/transfer/",
        "parser": parse_1tv_now,
        "stream_prefix": "https://1tv.ru",
    },
    "RENTV": {
        "url": "https://www.rentv.ru/program/",
        "parser": parse_ctc_now,
        "stream_prefix": "https://rentv.ru",
    },
}

OUTPUT_FILE = "../data/schedule.json"

def load_m3u(url):
    text = fetch(url)
    if not text:
        return []
    channels = []
    name = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            name = line.split(",", 1)[-1].strip()
        elif line.startswith("http"):
            channels.append({"name": name, "url": line})
    return channels

def get_channel_schedule(name):
    mapped = None
    for key, val in CHANNEL_MAP.items():
        if key.lower() in name.lower():
            mapped = val
            break
    if not mapped:
        return None

    html = fetch(mapped["url"])
    if not html:
        return None

    program_title = mapped["parser"](html)

    # Грубый эвристический поиск stream_url — можно улучшить
    # Тут — просто заглушка, реальные URL будут в следующем шаге
    stream_url = f"{mapped['stream_prefix']}/playlist.m3u8"

    return {
        "channel": name,
        "program": program_title,
        "is_live": True,
        "start": "18:00",
        "end": "21:00",
        "stream_url": stream_url,
    }

def main():
    print("🔍 Starting schedule scrape...")

    all_channels = []
    for src in M3U_SOURCES:
        all_channels.extend(load_m3u(src))

    # Уникализация по имени
    unique = {}
    for ch in all_channels:
        unique[ch["name"]] = ch

    schedule = []
    for name, ch in list(unique.items())[:20]:  # первые 20 каналов
        data = get_channel_schedule(name)
        if data:
            # Пытаемся заменить stream_url на реальный из m3u (если найден)
            data["stream_url"] = ch["url"] or data["stream_url"]
            schedule.append(data)
            print(f"✅ Scraped: {name} — {data['program']}")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    print(f"📄 Saved {len(schedule)} channels to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
