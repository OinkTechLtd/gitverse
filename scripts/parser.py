import requests
import json
import os
import re
from datetime import datetime

# Прямые источники плейлистов
PLAYLIST_URLS = [
    "https://raw.githubusercontent.com/oinktechllc/livem3u/main/live.m3u",
    "https://raw.githubusercontent.com/oinktechltd/rulive/main/live.m3u"
]

def get_real_program(channel_name):
    """Улучшенный поиск программы по нескольким источникам"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
    
    # Источник 1: tv.mail.ru
    try:
        search_url = f"https://tv.mail.ru/search/?q={channel_name}"
        resp = requests.get(search_url, headers=headers, timeout=5)
        # Ищем через регулярки более гибко
        titles = re.findall(r'"p-channels__item__info__title">(.*?)<', resp.text)
        if titles:
            print(f"[OK] Нашел на Mail.ru: {titles[0]}")
            return titles[0], 45
    except:
        pass

    # Источник 2: Яндекс (упрощенный парсинг заголовка)
    try:
        y_url = f"https://yandex.ru/search/?text=программа+передач+{channel_name}+сейчас"
        resp = requests.get(y_url, headers=headers, timeout=5)
        if "сейчас в эфире" in resp.text.lower():
            print(f"[OK] Нашел упоминание на Яндексе для {channel_name}")
            return "В эфире: Смотрите сейчас", 30
    except:
        pass

    return "Прямой эфир", 10

def parse_m3u(url):
    print(f"[*] Сканирую плейлист: {url}")
    channels = []
    try:
        response = requests.get(url, timeout=10)
        # Улучшенная регулярка для M3U
        matches = re.findall(r'#EXTINF:.*?,(.*?)\n(http.*?)(?:\n|$)', response.text, re.DOTALL)
        for name, link in matches:
            channels.append({
                'name': name.strip(),
                'url': link.strip()
            })
        print(f"[+] Найдено каналов в списке: {len(channels)}")
        return channels
    except Exception as e:
        print(f"[!] Ошибка плейлиста {url}: {e}")
        return []

def main():
    print("🤖 Робот сканирует сеть...")
    raw_channels = []
    for url in PLAYLIST_URLS: raw_channels.extend(parse_m3u(url))
    
    seen = set()
    unique_channels = []
    for c in raw_channels:
        if c['name'].lower() not in seen:
            unique_channels.append(c)
            seen.add(c['name'].lower())

    final_data = []
    for ch in unique_channels[:30]:
        print(f"[*] Парсим эфир: {ch['name']}")
        title, progress = get_real_program(ch['name'])
        final_data.append({
            "name": ch['name'],
            "url": ch['url'],
            "logo": ch.get('logo', ''),
            "program": title,
            "progress": progress
        })

    # Ультимативный поиск пути
    base_path = os.getcwd()
    if os.path.exists(os.path.join(base_path, 'live-programm')):
        data_dir = os.path.join(base_path, 'live-programm', 'data')
    else:
        data_dir = os.path.join(base_path, 'data')
        
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, 'schedule.json')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    print(f"✅ Данные сохранены в {file_path}")

if __name__ == "__main__":
    main()
