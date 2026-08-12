# -*- coding: utf-8 -*-
"""2026-08-13 盘前：更新事件库(新增今日14条 + 回填昨日美股医药2条)"""
import json, os, glob

base = "/Users/jieyang/Documents/WealthHub"
events_dir = os.path.join(base, "data/processed/events")
news_path = os.path.join(base, "data/processed/news/sentiment-2026-08-13.json")

# 读取全部历史事件
all_events = []
for f in sorted(glob.glob(os.path.join(events_dir, "events-*.json"))):
    with open(f, encoding="utf-8") as fh:
        all_events.extend(json.load(fh))
print(f"历史事件库累计: {len(all_events)} 条 (含今日前)")

# 现有 ID 集合
existing_ids = {e["id"] for e in all_events}
print(f"已用 ID: {len(existing_ids)}")

# 生成今日新事件 ID（日期前缀 + 序号）
today = "2026-08-13"
prefix = f"N{today.replace('-', '')}"
today_events = [e for e in all_events if e["id"].startswith(prefix)]
print(f"今日已存在: {len(today_events)} 条")

with open(news_path, encoding="utf-8") as f:
    news = json.load(f)

# track 映射
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
        "track": track_map.get(n["category"], "其他"),
        "category": n["category"],
        "title": n["title"],
        "summary": n["summary"][:300],
        "source": "WebSearch",
        "source_url": n.get("source_url", ""),
        "sentiment": n["sentiment"],
        "strength": n["score"],
        "impact_direction": n["direction"],
        "expected_volatility": n["volatility"],
        "reason": n.get("reason", ""),
        "reference": "",
    }
    new_events.append(ev)

print(f"今日新增 {len(new_events)} 条")

# 写入今日事件文件
out = os.path.join(events_dir, f"events-{today}.json")
existing_today = []
if os.path.exists(out):
    with open(out, encoding="utf-8") as f:
        existing_today = json.load(f)

# 合并去重（按 id）
combined = {e["id"]: e for e in existing_today}
for e in new_events:
    combined[e["id"]] = e
combined_list = sorted(combined.values(), key=lambda x: x["id"])
with open(out, "w", encoding="utf-8") as f:
    json.dump(combined_list, f, ensure_ascii=False, indent=2)
print(f"写入 {out}: {len(combined_list)} 条")

# 汇总统计
total = len(all_events) + len(new_events)
print(f"事件库累计(含今日): {total} 条")
