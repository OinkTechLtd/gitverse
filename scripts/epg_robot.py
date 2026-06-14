#!/usr/bin/env python3
"""
live-programm | Умный поисковой робот EPG v2
Сам находит каналы + расписание без ручных подсказок
OinkTech Ltd | FUN RUSSIA CRMP
"""

import asyncio, aiohttp, json, re, logging, sys, os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ── Логи ──────────────────────────────────────────────────────
Path("data").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler("data/robot.log", encoding="utf-8")]
)
log = logging.getLogger("epg")
MSK = timezone(timedelta(hours=3))

# ══════════════════════════════════════════════════════════════
# ИЗВЕСТНЫЕ КАНАЛЫ — стартовый список, робот расширяет сам
# ══════════════════════════════════════════════════════════════
SEED_CHANNELS = [
    # Федеральные
    {"id":"perviy",   "name":"Первый канал",   "aliases":["1tv","первый","1 канал","channel one"],"group":"Федеральные","site_id":"1tv"},
    {"id":"rossiya1", "name":"Россия 1",        "aliases":["russia1","россия1","russia 1"],        "group":"Федеральные","site_id":"russia1"},
    {"id":"ntv",      "name":"НТВ",             "aliases":["ntv","нтв"],                           "group":"Федеральные","site_id":"ntv"},
    {"id":"ctc",      "name":"СТС",             "aliases":["ctc","стс"],                           "group":"Федеральные","site_id":"ctc"},
    {"id":"ren",      "name":"РЕН ТВ",          "aliases":["rentv","рен","ren tv"],                "group":"Федеральные","site_id":"rentv"},
    {"id":"tnt",      "name":"ТНТ",             "aliases":["tnt","тнт"],                           "group":"Федеральные","site_id":"tnt"},
    {"id":"5tv",      "name":"Пятый канал",     "aliases":["5tv","пятый","5 канал","russia5"],     "group":"Федеральные","site_id":"5tv"},
    {"id":"tvc",      "name":"ТВ Центр",        "aliases":["tvc","тв центр","tvcenter"],           "group":"Федеральные","site_id":"tvc"},
    {"id":"o_tv",     "name":"ОТР",             "aliases":["otr","отр"],                           "group":"Федеральные","site_id":"otr"},
    {"id":"zvez",     "name":"Звезда",          "aliases":["zvezda","звезда"],                     "group":"Федеральные","site_id":"zvezda"},
    {"id":"tb3",      "name":"ТВ-3",            "aliases":["tv3","тв3","тв-3"],                    "group":"Развлечения","site_id":"tv3"},
    {"id":"sas",      "name":"Суббота!",        "aliases":["subbota","суббота"],                   "group":"Развлечения","site_id":"subbota"},
    {"id":"chetv",    "name":"Четвёрка",        "aliases":["chetvertiy","четвёрка","4 канал"],     "group":"Развлечения","site_id":"chetvertiy"},
    {"id":"dom_kino", "name":"Дом Кино",        "aliases":["domkino","дом кино"],                  "group":"Кино",        "site_id":"domkino"},
    {"id":"karusel",  "name":"Карусель",        "aliases":["karusel","карусель"],                  "group":"Детские",    "site_id":"karusel"},
    {"id":"nauka",    "name":"Наука",           "aliases":["nauka","наука"],                       "group":"Познание",   "site_id":"nauka"},
    {"id":"muz",      "name":"МУЗ-ТВ",         "aliases":["muztv","муз тв","муз-тв"],             "group":"Музыка",     "site_id":"muztv"},
    {"id":"match",    "name":"Матч! ТВ",        "aliases":["matchtv","матч тв","match tv"],        "group":"Спорт",      "site_id":"matchtv"},
    {"id":"russia24", "name":"Россия 24",       "aliases":["russia24","россия 24","вести"],        "group":"Новости",    "site_id":"russia24"},
    {"id":"dozhd",    "name":"Дождь",           "aliases":["tvrain","дождь","rain tv"],            "group":"Новости",    "site_id":"tvrain"},
    # Дополнительные
    {"id":"mts_tv",   "name":"МТС ТВ",         "aliases":["mts tv","мтс"],                        "group":"Развлечения","site_id":"mts"},
    {"id":"tbk",      "name":"Москва 24",       "aliases":["moscow24","москва 24","m24"],          "group":"Новости",    "site_id":"moscow24"},
    {"id":"rtvi",     "name":"RTVI",            "aliases":["rtvi","рт вайн"],                      "group":"Новости",    "site_id":"rtvi"},
    {"id":"tbkino",   "name":"Кино ТВ",        "aliases":["kinotv","кино тв"],                    "group":"Кино",        "site_id":"kinotv"},
    {"id":"euronews", "name":"Euronews",        "aliases":["euronews","евроньюс"],                 "group":"Новости",    "site_id":"euronews"},
    {"id":"natgeo",   "name":"National Geographic","aliases":["natgeo","national geographic"],     "group":"Познание",   "site_id":"natgeo"},
    {"id":"discov",   "name":"Discovery",       "aliases":["discovery"],                           "group":"Познание",   "site_id":"discovery"},
    {"id":"ani_com",  "name":"Мульт",          "aliases":["mult","мульт"],                        "group":"Детские",    "site_id":"mult"},
    {"id":"nickel",   "name":"Nickelodeon",    "aliases":["nickelodeon","nick"],                   "group":"Детские",    "site_id":"nickelodeon"},
    {"id":"boomerang","name":"Boomerang",       "aliases":["boomerang"],                           "group":"Детские",    "site_id":"boomerang"},
    {"id":"sport1",   "name":"Спорт 1",        "aliases":["sport1","спорт 1"],                    "group":"Спорт",      "site_id":"sport1"},
    {"id":"football", "name":"Футбол 1",       "aliases":["football1","футбол 1"],                "group":"Спорт",      "site_id":"football1"},
]

# ══════════════════════════════════════════════════════════════
# EPG ИСТОЧНИКИ (публичные, без авторизации)
# ══════════════════════════════════════════════════════════════
EPG_XMLTV_SOURCES = [
    # Публичные XMLTV файлы
    "https://epg.one/epg.xml",
    "https://epg.ottplay.com/epg/russia.xml",
    "https://raw.githubusercontent.com/dp247/Freeview-EPG/master/epg.xml",
    "https://www.open-epg.com/files/russia1.xml",
    "https://epg.iptvx.one/epg.xml",
]

# Сайты с расписанием для веб-парсинга
SCHEDULE_APIS = [
    {
        "id":   "tvmail",
        "name": "tv.mail.ru",
        "url":  "https://tv.mail.ru/ajax/channel/?channel_id={channel_num}&region_id=8&date={date}",
        # Сопоставление наших id → числовые id tv.mail.ru
        "ids":  {
            "perviy":"1","rossiya1":"2","ntv":"3","ctc":"11",
            "ren":"7","tnt":"20","5tv":"5","tvc":"9","zvez":"25",
            "tb3":"14","russia24":"33","match":"60","muz":"16",
            "sas":"58","karusel":"46","nauka":"34","dozhd":"76",
            "o_tv":"55","dom_kino":"51",
        },
    },
    {
        "id":   "jtv",
        "name": "jtvru.com",
        "url":  "https://jtvru.com/epg/{site_id}/{date}.json",
    },
    {
        "id":   "epgbest",
        "name": "epg.best",
        "url":  "https://epg.best/ch/{site_id}/{date}.json",
    },
    {
        "id":   "rp5",
        "name": "russianprogramm",
        "url":  "https://programm.philo.ru/tv/channel/{site_id}/date/{date}",
        "type": "html",
    },
]

HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "application/json,text/html,*/*;q=0.8",
}


# ══════════════════════════════════════════════════════════════
class EPGRobot:

    def __init__(self):
        self.channels = {ch["id"]: ch for ch in SEED_CHANNELS}
        self.schedule = {}   # channel_id → [prog, ...]
        self.sess = None

    async def run(self):
        log.info("🤖 Запуск EPG-робота v2 ...")
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=20, ssl=False)
        async with aiohttp.ClientSession(headers=HDR, timeout=timeout, connector=connector) as sess:
            self.sess = sess

            # 1. Пробуем загрузить публичные XMLTV
            log.info("📡 Шаг 1: поиск в публичных XMLTV-источниках...")
            await self.fetch_xmltv_sources()

            # 2. Добираем через API для каналов без расписания
            missing = [ch for ch in self.channels.values() if not self.schedule.get(ch["id"])]
            log.info(f"🔍 Шаг 2: API-поиск для {len(missing)} каналов без расписания...")
            await self.fetch_via_apis(missing)

            # 3. Авто-обнаружение новых каналов из XMLTV
            log.info("🆕 Шаг 3: поиск новых каналов...")
            await self.discover_new_channels()

            # 4. Плейлисты OinkTech — матчим каналы
            log.info("📺 Шаг 4: загрузка плейлистов OinkTech...")
            await self.load_oinktech_playlists()

        total_progs = sum(len(v) for v in self.schedule.values())
        log.info(f"✅ Итого: {len(self.schedule)} каналов, {total_progs} передач")
        self.save()

    # ── XMLTV источники ───────────────────────────────────────
    async def fetch_xmltv_sources(self):
        for url in EPG_XMLTV_SOURCES:
            try:
                log.info(f"  → {url}")
                async with self.sess.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
                    if r.status != 200:
                        continue
                    xml_bytes = await r.read()
                count = self.parse_xmltv(xml_bytes)
                log.info(f"  ✅ Получено {count} программ")
                if count > 100:
                    break  # достаточно
            except Exception as e:
                log.debug(f"  ⚠️  {url}: {e}")

    def parse_xmltv(self, xml_bytes):
        """Парсим XMLTV и матчим каналы по названию"""
        count = 0
        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError:
            # Попытка обрезать плохие байты
            try:
                root = ET.fromstring(xml_bytes.decode("utf-8", errors="ignore").encode())
            except Exception:
                return 0

        # Строим карту xmltv_id → наш channel_id
        id_map = {}
        for ch_el in root.findall("channel"):
            xml_id = ch_el.get("id", "")
            names = [n.text or "" for n in ch_el.findall("display-name")]
            our_id = self.match_channel_name(names + [xml_id])
            if our_id:
                id_map[xml_id] = our_id

        now_ts = _now_ts()
        window_start = now_ts - 3600
        window_end   = now_ts + 86400 * 2  # 2 дня вперёд

        for prog in root.findall("programme"):
            xml_id = prog.get("channel", "")
            our_id = id_map.get(xml_id)
            if not our_id:
                continue

            start = parse_xmltv_time(prog.get("start", ""))
            stop  = parse_xmltv_time(prog.get("stop",  ""))
            if not start or not stop:
                continue
            if stop < window_start or start > window_end:
                continue

            title_el = prog.find("title")
            title = (title_el.text or "") if title_el is not None else ""
            if not title:
                continue

            desc_el = prog.find("desc")
            desc = (desc_el.text or "") if desc_el is not None else ""
            cat_el = prog.find("category")
            genre = (cat_el.text or "") if cat_el is not None else ""

            if our_id not in self.schedule:
                self.schedule[our_id] = []

            self.schedule[our_id].append({
                "channel": our_id,
                "title":   title.strip(),
                "start":   int(start),
                "stop":    int(stop),
                "desc":    desc.strip(),
                "genre":   genre.strip(),
                "live":    int(start) <= now_ts < int(stop),
            })
            count += 1

        # Сортируем
        for cid in self.schedule:
            self.schedule[cid].sort(key=lambda x: x["start"])
            # Убираем дубли
            seen = set()
            uniq = []
            for p in self.schedule[cid]:
                k = (p["start"], p["title"])
                if k not in seen:
                    seen.add(k)
                    uniq.append(p)
            self.schedule[cid] = uniq

        return count

    # ── API поиск для конкретных каналов ─────────────────────
    async def fetch_via_apis(self, channels):
        today = datetime.now(MSK).strftime("%Y-%m-%d")
        tasks = [self.fetch_one_channel(ch, today) for ch in channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for ch, res in zip(channels, results):
            if isinstance(res, list) and res:
                self.schedule[ch["id"]] = res
                log.info(f"  ✅ {ch['name']}: {len(res)} передач (API)")

    async def fetch_one_channel(self, ch, date):
        """Перебираем API источники для одного канала"""
        for api in SCHEDULE_APIS:
            try:
                progs = await self.try_api(api, ch, date)
                if progs:
                    return progs
            except Exception as e:
                log.debug(f"  {api['name']} / {ch['name']}: {e}")
        # Fallback: генерируем заглушку
        return self.make_placeholder(ch)

    async def try_api(self, api, ch, date):
        if api["id"] == "tvmail":
            num = api["ids"].get(ch["id"])
            if not num:
                return []
            url = api["url"].format(channel_num=num, date=date)
        else:
            url = api["url"].format(site_id=ch["site_id"], date=date)

        async with self.sess.get(url) as r:
            if r.status != 200:
                return []
            ct = r.headers.get("Content-Type", "")
            if "json" in ct:
                data = await r.json(content_type=None)
            else:
                data = await r.text()

        return self.parse_api_response(api["id"], data, ch)

    def parse_api_response(self, api_id, data, ch):
        now_ts = _now_ts()
        progs = []

        if api_id == "tvmail":
            items = []
            if isinstance(data, dict):
                items = data.get("rows", data.get("schedule", []))
            elif isinstance(data, list):
                items = data
            for it in items:
                title = it.get("title") or it.get("name","")
                if not title: continue
                start = _to_ts(it.get("start_ut") or it.get("start_time") or it.get("start"))
                stop  = _to_ts(it.get("end_ut")   or it.get("end_time")   or it.get("stop"))
                if not start: continue
                if not stop: stop = start + 3600
                progs.append(_p(ch["id"], title, start, stop,
                               it.get("description",""), it.get("genre",""), now_ts))

        elif api_id in ("epgbest","jtv"):
            items = data if isinstance(data, list) else data.get("schedule", []) if isinstance(data,dict) else []
            for it in items:
                title = it.get("title") or it.get("name","")
                if not title: continue
                start = _to_ts(it.get("start") or it.get("time"))
                stop  = _to_ts(it.get("stop")  or it.get("end"))
                if not start: continue
                if not stop: stop = start + 3600
                progs.append(_p(ch["id"], title, start, stop, it.get("desc",""), "", now_ts))

        elif api_id == "rp5" and isinstance(data, str):
            # HTML парсинг — ищем паттерны времени + название
            for m in re.finditer(r'(\d{1,2}:\d{2})[^\w]*([^\n<]{4,80})', data):
                t, name = m.group(1), m.group(2).strip()
                name = re.sub(r'\s+', ' ', name)
                if len(name) < 3 or len(name) > 100: continue
                h, mi = map(int, t.split(":"))
                dt = datetime.now(MSK).replace(hour=h, minute=mi, second=0, microsecond=0)
                progs.append(_p(ch["id"], name, int(dt.timestamp()), int(dt.timestamp())+3600, "", "", now_ts))

        return progs

    # ── Авто-обнаружение новых каналов ───────────────────────
    async def discover_new_channels(self):
        """
        Загружаем XMLTV ещё раз и ищем каналы которых у нас ещё нет.
        Добавляем их в self.channels автоматически.
        """
        try:
            url = EPG_XMLTV_SOURCES[0]
            async with self.sess.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
                if r.status != 200: return
                xml_bytes = await r.read()
            root = ET.fromstring(xml_bytes)
        except Exception as e:
            log.debug(f"discover: {e}")
            return

        # Уже известные имена (нижний регистр)
        known_names = set()
        for ch in self.channels.values():
            known_names.add(ch["name"].lower())
            for a in ch.get("aliases", []):
                known_names.add(a.lower())

        added = 0
        for ch_el in root.findall("channel"):
            xml_id = ch_el.get("id","")
            names = [n.text or "" for n in ch_el.findall("display-name") if n.text]
            if not names: continue
            primary = names[0]
            low = primary.lower()

            # Уже знаем?
            if any(low == kn for kn in known_names): continue
            if self.match_channel_name(names): continue

            # Определяем группу автоматически по ключевым словам
            group = auto_group(primary)

            # Генерируем id
            safe_id = re.sub(r'[^a-z0-9]', '_', low)[:20].strip('_') or f"ch_{len(self.channels)}"
            if safe_id in self.channels:
                safe_id += f"_{len(self.channels)}"

            new_ch = {
                "id":      safe_id,
                "name":    primary,
                "aliases": [n.lower() for n in names[1:]],
                "group":   group,
                "site_id": xml_id,
                "auto":    True,  # отмечаем как авто-найденный
            }
            self.channels[safe_id] = new_ch
            known_names.add(low)
            added += 1
            if added >= 200:  # не добавляем бесконечно
                break

        if added:
            log.info(f"  🆕 Авто-найдено {added} новых каналов")

    # ── Загрузка плейлистов OinkTech ─────────────────────────
    async def load_oinktech_playlists(self):
        urls = [
            "https://raw.githubusercontent.com/OinkTechLLC/livem3u/refs/heads/main/zabava-full.m3u",
            "https://raw.githubusercontent.com/OinkTechLtd/rulive/refs/heads/main/russ.m3u",
            "https://raw.githubusercontent.com/OinkTechLLC/livem3u/refs/heads/main/smotrim.m3u",
        ]
        stream_map = {}  # channel_name_lower → url
        for url in urls:
            try:
                async with self.sess.get(url) as r:
                    if r.status != 200: continue
                    txt = await r.text()
                self.parse_m3u_into(txt, stream_map)
            except Exception as e:
                log.debug(f"playlist {url}: {e}")

        # Прикрепляем stream_url к каналам
        matched = 0
        for ch in self.channels.values():
            if ch.get("stream_url"): continue
            names_to_try = [ch["name"].lower()] + [a.lower() for a in ch.get("aliases",[])]
            for n in names_to_try:
                if n in stream_map:
                    ch["stream_url"] = stream_map[n]
                    matched += 1
                    break
        log.info(f"  📡 Плейлист: {matched} каналов со стримами")

    def parse_m3u_into(self, txt, out):
        meta = {}
        for line in txt.splitlines():
            line = line.strip()
            if line.startswith("#EXTINF"):
                name = (re.search(r',(.+)$', line) or [None,""])[1].strip()
                meta = {"name": name}
            elif line and not line.startswith("#") and meta.get("name"):
                out[meta["name"].lower()] = line
                meta = {}

    # ── Сопоставление по имени ────────────────────────────────
    def match_channel_name(self, names):
        for ch in self.channels.values():
            all_names = [ch["name"].lower()] + [a.lower() for a in ch.get("aliases",[])]
            for n in names:
                nl = n.lower().strip()
                if any(nl == a or nl in a or a in nl for a in all_names):
                    return ch["id"]
        return None

    # ── Заглушка расписания ───────────────────────────────────
    def make_placeholder(self, ch):
        now = datetime.now(MSK)
        now_ts = _now_ts()
        slots = [
            (6,0,"Утреннее вещание"),
            (9,0,"Утренние программы"),
            (12,0,"Дневной эфир"),
            (15,0,"Дневные программы"),
            (18,0,"Вечерние новости"),
            (20,0,"Прайм-тайм"),
            (22,0,"Ночное вещание"),
        ]
        progs = []
        for i, (h,m,title) in enumerate(slots):
            dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if i+1 < len(slots):
                nh, nm, _ = slots[i+1]
                edt = now.replace(hour=nh, minute=nm, second=0, microsecond=0)
            else:
                edt = now.replace(hour=23, minute=59, second=0, microsecond=0)
            progs.append(_p(ch["id"], title, int(dt.timestamp()), int(edt.timestamp()), "", "", now_ts))
        return progs

    # ── Сохранение ────────────────────────────────────────────
    def save(self):
        now = datetime.now(MSK)
        # Обновляем live-флаги
        now_ts = _now_ts()
        for cid, progs in self.schedule.items():
            for p in progs:
                p["live"] = p["start"] <= now_ts < p["stop"]

        out = {
            "updated":    now.isoformat(),
            "updated_ts": now_ts,
            "channels":   self.channels,
            "schedule":   self.schedule,
        }
        Path("data/schedule.json").write_text(
            json.dumps(out, ensure_ascii=False, separators=(",",":")),
            encoding="utf-8"
        )
        log.info("💾 data/schedule.json сохранён")
        self.save_xmltv(now)

    def save_xmltv(self, now):
        root = ET.Element("tv", {
            "date": now.strftime("%Y%m%d%H%M%S +0300"),
            "source-info-name": "live-programm.oinktech.ltd",
            "generator-info-name": "OinkTech EPG Robot v2",
        })
        for ch in self.channels.values():
            c = ET.SubElement(root, "channel", id=ch["id"])
            ET.SubElement(c, "display-name", lang="ru").text = ch["name"]
            if ch.get("stream_url"):
                ET.SubElement(c, "url").text = ch["stream_url"]

        fmt = "%Y%m%d%H%M%S +0300"
        for ch in self.channels.values():
            for p in self.schedule.get(ch["id"], []):
                el = ET.SubElement(root, "programme", {
                    "start":   datetime.fromtimestamp(p["start"], MSK).strftime(fmt),
                    "stop":    datetime.fromtimestamp(p["stop"],  MSK).strftime(fmt),
                    "channel": ch["id"],
                })
                ET.SubElement(el, "title", lang="ru").text = p["title"]
                if p.get("desc"):
                    ET.SubElement(el, "desc", lang="ru").text = p["desc"]
                if p.get("genre"):
                    ET.SubElement(el, "category", lang="ru").text = p["genre"]

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write("data/epg.xml", encoding="utf-8", xml_declaration=True)
        log.info("📡 data/epg.xml сохранён")


# ══════════════════════════════════════════════════════════════
# Утилиты
# ══════════════════════════════════════════════════════════════

def _now_ts():
    return int(datetime.now(MSK).timestamp())

def _to_ts(v):
    if v is None: return None
    if isinstance(v, (int,float)): return float(v)
    if isinstance(v, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%d %H:%M:%S","%H:%M:%S","%H:%M"):
            try:
                dt = datetime.strptime(v[:len(fmt)], fmt)
                if dt.year == 1900:
                    n = datetime.now(MSK)
                    dt = dt.replace(year=n.year, month=n.month, day=n.day)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=MSK)
                return dt.timestamp()
            except ValueError:
                pass
    return None

def parse_xmltv_time(s):
    """20240115143000 +0300"""
    if not s: return None
    s = s.strip()
    try:
        m = re.match(r'(\d{14})\s*([+-]\d{4})?', s)
        if not m: return None
        dt = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
        tz_str = m.group(2) or "+0300"
        sign = 1 if tz_str[0]=='+' else -1
        h, mi = int(tz_str[1:3]), int(tz_str[3:5])
        tz = timezone(timedelta(hours=sign*h, minutes=sign*mi))
        return dt.replace(tzinfo=tz).timestamp()
    except Exception:
        return None

def _p(cid, title, start, stop, desc, genre, now_ts):
    return {
        "channel": cid,
        "title":   title,
        "start":   int(start),
        "stop":    int(stop),
        "desc":    desc or "",
        "genre":   genre or "",
        "live":    int(start) <= now_ts < int(stop),
    }

def auto_group(name):
    n = name.lower()
    if any(w in n for w in ["новост","news","вести","24","rtvi","euronews","cnn","bbc"]): return "Новости"
    if any(w in n for w in ["спорт","sport","матч","match","футбол","хоккей","бокс"]): return "Спорт"
    if any(w in n for w in ["кино","movie","film","cinema","дом кино","premier"]): return "Кино"
    if any(w in n for w in ["дет","kids","cartoon","мульт","nick","disney","карусель","boomerang"]): return "Детские"
    if any(w in n for w in ["муз","music","муz","mtv","vh1","jazz","rock"]): return "Музыка"
    if any(w in n for w in ["наук","science","discovery","national","geo","viasat","history"]): return "Познание"
    return "Развлечения"


if __name__ == "__main__":
    asyncio.run(EPGRobot().run())
