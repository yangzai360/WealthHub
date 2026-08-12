#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-12 盘中档: 追加事件库 JSON (013-018) + 历史同类匹配
读 sentiment-2026-08-12.json(全部) + news-2026-08-12.json -> 合并进 events-2026-08-12.json
仅新增 sentiment 中未入库的事件; 保留盘前已入库条目(含 reference 匹配)
"""
import json, os, glob

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS = os.path.join(BASE, "data/processed/news")
EVENTS = os.path.join(BASE, "data/processed/events")

with open(os.path.join(NEWS, "sentiment-2026-08-12.json"), encoding="utf-8") as f:
    senti = json.load(f)
with open(os.path.join(NEWS, "news-2026-08-12.json"), encoding="utf-8") as f:
    news = json.load(f)
nmap = {n["id"]: n for n in news}

# 已入库事件
events_path = os.path.join(EVENTS, "events-2026-08-12.json")
with open(events_path, encoding="utf-8") as f:
    existing = json.load(f)
existing_ids = {e["id"] for e in existing}
print(f"已入库: {len(existing)} 条, 需匹配 sentiment: {len(senti)} 条")

# 历史事件库 (不含今日)
hist_events = []
for fp in sorted(glob.glob(os.path.join(EVENTS, "events-2026-08-*.json"))):
    if "2026-08-12" in fp:
        continue
    with open(fp, encoding="utf-8") as f:
        hist_events.extend(json.load(f))

# 关键词匹配 (与盘前脚本一致)
KW = {
    "A股医药": ["创新药", "医药", "BD", "出海", "中报", "药企", "FDA", "集采", "ETF", "CRO", "临床", "GLP", "医保", "百济", "药明"],
    "大消费": ["白酒", "茅台", "五粮液", "消费", "酒价", "批价", "提价", "中秋", "猪", "乳品", "国窖"],
    "恒生科技": ["腾讯", "港股", "恒生", "恒科", "南向", "中概", "互联网", "科网", "阿里", "视频号", "AI", "云"],
    "美股标普医药": ["礼来", "GLP", "减肥药", "医疗", "默沙东", "强生", "XLV", "美股医药", "FDA", "MNC", "药王"],
    "宏观": ["CPI", "美联储", "加息", "美股", "利率", "原油", "油价", "非农", "美债", "通胀", "FOMC"],
}

def match_hist(ev):
    t = ev.get("track", "")
    title = ev.get("title", "")
    kws = KW.get(t, [])
    cands = []
    for h in hist_events:
        score = 0
        ht = h.get("track", "")
        htitle = h.get("title", "")
        if ht == t:
            score += 2
        for kw in kws:
            if kw.lower() in htitle.lower():
                score += 1
        if score >= 3:
            cands.append((score, h))
    cands.sort(key=lambda x: -x[0])
    top3 = cands[:3]
    conf = 55 + min(20, len(top3) * 5)
    titles = [f"{h['date']} {h['title'][:45]}({h['track']})" for _, h in top3]
    return titles, conf

added = 0
for s in senti:
    if s["id"] in existing_ids:
        continue
    n = nmap[s["id"]]
    titles, conf = match_hist(s)
    ev = {
        "id": s["id"], "date": "2026-08-12", "track": s["track"],
        "category": s["category"], "title": s["title"],
        "summary": n["summary"][:260], "source": n["source"],
        "source_url": s["source_url"],
        "sentiment": s["sentiment"], "strength": s["strength"],
        "impact_direction": s["impact_direction"],
        "expected_volatility": s["expected_volatility"],
        "reason": s["reason"],
        "reference": {
            "ret_3d": None, "ret_5d": None, "ret_10d": None, "max_vol": None,
            "confidence": conf if titles else None,
            "actual_ret_1d": None, "actual_date": None,
            "ret_1d_ref": None,
            "match_titles": titles,
        }
    }
    existing.append(ev)
    existing_ids.add(s["id"])
    added += 1
    print(f"  + {ev['id']} {ev['track']} {ev['sentiment']}{ev['strength']} 匹配{len(titles)}条 置信度{conf}")

with open(events_path, "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False, indent=1)
print(f"\n事件库共 {len(existing)} 条, 新增 {added} 条")
