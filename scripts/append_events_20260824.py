# -*- coding: utf-8 -*-
"""周一(8/24)盘前档:追加盘前事件到事件库(events-2026-08-24.json)"""
import json, os

EVENTS_PATH = '/Users/jieyang/Documents/WealthHub/data/processed/events/events-2026-08-24.json'
NEWS_PATH = '/Users/jieyang/Documents/WealthHub/data/processed/news/news-2026-08-24.json'

with open(NEWS_PATH, encoding='utf-8') as f:
    news = json.load(f)

events = []
for i, n in enumerate(news, 1):
    events.append({
        "id": f"N20260824-{i:03d}",
        "date": "2026-08-24",
        "track": n['track'],
        "category": n['category'],
        "title": n['title'],
        "summary": n['summary'],
        "source": "WebSearch",
        "source_url": n.get('source_url', ''),
        "sentiment": n.get('sentiment', '中性'),
        "score": n.get('score', 50),
        "strength": n.get('strength', 50),
        "direction": n.get('direction', '中性'),
        "volatility": n.get('volatility', '中'),
        "reason": n.get('comment', ''),
        "reference": {
            "ret_3d": None,
            "ret_5d": None,
            "ret_10d": None,
            "max_vol": None,
            "confidence": None,
            "actual_ret_1d": None,
            "note": "盘前事件,actual_ret_1d 待 8/24(周一)收盘回填",
            "ret_1d_ref": None,
        }
    })

with open(EVENTS_PATH, 'w', encoding='utf-8') as f:
    json.dump(events, f, ensure_ascii=False, indent=1)
print(f'事件库写入 {len(events)} 条 -> {EVENTS_PATH}')
