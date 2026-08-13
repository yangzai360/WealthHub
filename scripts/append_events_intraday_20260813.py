# -*- coding: utf-8 -*-
"""2026-08-13 盘中: 追加盘中7条新闻到事件库"""
import json, os, glob

base = "/Users/jieyang/Documents/WealthHub"
events_dir = os.path.join(base, "data/processed/events")

# 读取全部历史事件
all_events = []
for f in sorted(glob.glob(os.path.join(events_dir, "events-*.json"))):
    with open(f, encoding="utf-8") as fh:
        all_events.extend(json.load(fh))
existing_ids = {e["id"] for e in all_events}
print(f"历史事件库累计(含盘前): {len(all_events)} 条")

# 读取 sentiment 最新（含盘中）
with open(os.path.join(base, "data/processed/news/sentiment-2026-08-13.json"), encoding="utf-8") as f:
    news = json.load(f)
print(f"今日 sentiment 共 {len(news)} 条")

today = "2026-08-13"
prefix = f"N{today.replace('-', '')}"
today_events = [e for e in all_events if e["id"].startswith(prefix)]
print(f"今日事件已存在: {len(today_events)} 条")

track_map = {
    "宏观类": "宏观", "业绩类": "业绩", "行业事件类": "行业事件", "政策类": "政策",
}

new_events = []
for i, n in enumerate(news, 1):
    eid = f"{prefix}-{i:03d}"
    if eid in existing_ids:
        continue
    ev = {
        "id": eid,
        "date": today,
        "track": track_map.get(n.get("category", ""), "其他"),
        "category": n.get("category", ""),
        "title": n.get("title", ""),
        "summary": n.get("summary", "")[:300],
        "source": "WebSearch",
        "source_url": n.get("source_url", ""),
        "sentiment": n.get("sentiment", "中性"),
        "strength": n.get("score", 50),
        "impact_direction": n.get("direction", "中性"),
        "expected_volatility": n.get("volatility", "中"),
        "reason": n.get("reason", ""),
        "reference": "",
    }
    new_events.append(ev)

print(f"本次新增 {len(new_events)} 条 (含盘前未入库的)")
out = os.path.join(events_dir, f"events-{today}.json")
existing_today = []
if os.path.exists(out):
    with open(out, encoding="utf-8") as f:
        existing_today = json.load(f)

combined = {e["id"]: e for e in existing_today}
for e in new_events:
    combined[e["id"]] = e
combined_list = sorted(combined.values(), key=lambda x: x["id"])
with open(out, "w", encoding="utf-8") as f:
    json.dump(combined_list, f, ensure_ascii=False, indent=2)
print(f"写入 {out}: {len(combined_list)} 条")

total = len(all_events) + len(new_events)
print(f"事件库累计(含今日): {total} 条")
