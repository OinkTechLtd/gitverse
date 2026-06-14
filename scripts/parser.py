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
    """Реальный поиск программы через открытые API или парсинг"""
    search_url = f"https://tv.mail.ru/search/?q={channel_name}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36"}
    
    try:
        resp = requests.get(search_url, headers=headers, timeout=5)
        # Ищем блок текущей передачи и время
        # Формат на сайте обычно: <span class="p-programms__item__time">20:00</span>
        times = re.findall(r'(\d{2}:\d{2})', resp.text)
        titles = re.findall(r'class="p-channels__item__info__title">(.*?)<', resp.text)
        
        if titles:
            current_title = titles[0]
            # Вычисляем прогресс если нашли время
            progress = 50 # Дефолт
            if len(times) >= 2:
                start_str = times[0]
                now = datetime.now()
                start_time = now.replace(hour=int(start_str.split(':')[0]), minute=int(start_str.split(':')[1]))
                # Упрощенный расчет прогресса
                elapsed = (now - start_time).seconds / 60
                progress = min(max(int((elapsed / 60) * 100), 10), 95) # От 10% до 95%
            
            return current_title, progress
    except:
        pass
    return "Прямой эфир", 0

def parse_m3u(url):
    channels = []
    try:
        response = requests.get(url, timeout=10)
        lines = response.text.split('\n')
        current = {}
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                name = re.search(r',(.+)$', line)
                current['name'] = name.group(1).strip() if name else "Unknown"
                logo = re.search(r'tvg-logo="([^"]+)"', line)
                if logo: current['logo'] = logo.group(1)
            elif line.startswith('http'):
                current['url'] = line
                channels.append(current)
                current = {}
        return channels
    except: return []

def main():
    print("🤖 Робот сканирует сеть...")
    raw_channels = []
    for url in PLAYLIST_URLS: raw_channels.extend(parse_m3u(url))
    
    # Фильтруем дубликаты
    seen = set()
    unique_channels = []
    for c in raw_channels:
        if c['name'].lower() not in seen:
            unique_channels.append(c)
            seen.add(c['name'].lower())

    final_data = []
    for ch in unique_channels[:30]: # Берем топ 30
        print(f"[*] Парсим эфир: {ch['name']}")
        title, progress = get_real_program(ch['name'])
        final_data.append({
            "name": ch['name'],
            "url": ch['url'],
            "logo": ch.get('logo', ''),
            "program": title,
            "progress": progress
        })

    # Путь относительно корня репозитория для GitHub Actions
    data_dir = 'live-programm/data'
    if not os.path.exists('live-programm'):
        data_dir = 'data' # Если запускаем локально из папки проекта
        
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, 'schedule.json')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    print(f"✅ Данные сохранены в {file_path}")

if __name__ == "__main__":
    main()
