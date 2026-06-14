#!/usr/bin/env python3
"""Сборщик статического сайта для GitHub Pages"""
import json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"
DATA = ROOT / "data"
DOCS.mkdir(exist_ok=True)
(DOCS / "data").mkdir(exist_ok=True)

def cp(src, dst):
    if Path(src).exists():
        shutil.copy(src, dst)
        print(f"  ✅ {Path(src).name}")
    else:
        print(f"  ⚠️  {src} не найден")

# --- Читаем данные ---
sched_path = DATA / "schedule.json"
epg_data   = {}
if sched_path.exists():
    epg_data = json.loads(sched_path.read_text("utf-8"))
    print(f"📊 schedule.json: {len(epg_data.get('channels',{}))} каналов, "
          f"{sum(len(v) for v in epg_data.get('schedule',{}).values())} передач")

def inject_data(html_path, out_path):
    if not Path(html_path).exists():
        print(f"  ⚠️  {html_path} не найден")
        return
    html = Path(html_path).read_text("utf-8")
    if epg_data:
        snippet = f"<script>window.__EPG_DATA__={json.dumps(epg_data, ensure_ascii=False, separators=(',',':'))};</script>"
        html = html.replace("</head>", snippet + "\n</head>", 1)
    Path(out_path).write_text(html, "utf-8")
    print(f"  ✅ {Path(out_path).name}")

print("🏗️  Копируем файлы...")
inject_data(ROOT / "index.html",  DOCS / "index.html")
inject_data(ROOT / "embed.html",  DOCS / "embed.html")
cp(ROOT / "player.html", DOCS / "player.html")

# Данные
for f in DATA.glob("*.json"):
    shutil.copy(f, DOCS / "data" / f.name)
for f in DATA.glob("*.xml"):
    shutil.copy(f, DOCS / "data" / f.name)

print("\n✅ docs/ собран")
