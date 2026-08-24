# -*- coding: utf-8 -*-
"""盘前档 2026-08-25：事件库追加 15 条（从 news/sentiment 读取，actual_ret_1d 待 8/25 收盘回填）"""
import json, os

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_PATH = os.path.join(BASE, 'data/processed/news/news-2026-08-25.json')
SENT_PATH = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-25.json')
EVT_PATH = os.path.join(BASE, 'data/processed/events/events-2026-08-25.json')

with open(NEWS_PATH, encoding='utf-8') as f:
    news = json.load(f)
with open(SENT_PATH, encoding='utf-8') as f:
    sentiments = json.load(f)

# 用 sentiment 为准构建事件（sentiment 已含 direction/volatility/comment）
evs = []
for i, s in enumerate(sentiments, 1):
    # 从 news 补 summary/source_url
    n = next((x for x in news if x['title'] == s['title']), {})
    evs.append({
        "id": f"N20260825-{i:03d}",
        "date": "2026-08-25",
        "track": s['track'],
        "category": n.get('category', ''),
        "title": s['title'],
        "summary": n.get('summary', ''),
        "source": "WebSearch",
        "source_url": n.get('source_url', ''),
        "sentiment": s['sentiment'],
        "score": s['score'],
        "strength": s['strength'],
        "direction": s['direction'],
        "volatility": s['volatility'],
        "reason": s['comment'],
        "reference": {
            "ret_3d": None,
            "ret_5d": None,
            "ret_10d": None,
            "max_vol": None,
            "confidence": None,
            "actual_ret_1d": None,
            "note": "盘前事件,actual_ret_1d 待 8/25(周二)收盘回填",
            "ret_1d_ref": "赛道指数/ETF收盘",
            "actual_date": "2026-08-25"
        }
    })

with open(EVT_PATH, 'w', encoding='utf-8') as f:
    json.dump(evs, f, ensure_ascii=False, indent=1)
print(f'事件库追加 {len(evs)} 条 -> events-2026-08-25.json')

# 统计总事件数
total = 0
for fn in sorted(os.listdir(os.path.join(BASE, 'data/processed/events'))):
    if fn.startswith('events-') and fn.endswith('.json'):
        with open(os.path.join(BASE, 'data/processed/events', fn), encoding='utf-8') as f:
            total += len(json.load(f))
print(f'事件库累计: {total} 条')
