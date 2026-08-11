#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-08-12 盘前档: 构建事件库 JSON + 历史同类匹配
读 sentiment-2026-08-12.json -> 匹配历史事件(events-08-06..08-11) -> events-2026-08-12.json
"""
import json, os, re, glob

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS = os.path.join(BASE, "data/processed/news")
EVENTS = os.path.join(BASE, "data/processed/events")

# ---------- 1. 读今日 sentiment ----------
with open(os.path.join(NEWS, "sentiment-2026-08-12.json"), encoding="utf-8") as f:
    senti = json.load(f)
with open(os.path.join(NEWS, "news-2026-08-12.json"), encoding="utf-8") as f:
    news = json.load(f)
nmap = {n["id"]: n for n in news}

# ---------- 2. 读历史事件库 ----------
hist_events = []
for fp in sorted(glob.glob(os.path.join(EVENTS, "events-2026-08-*.json"))):
    if "2026-08-12" in fp:
        continue
    with open(fp, encoding="utf-8") as f:
        hist_events.extend(json.load(f))
print(f"历史事件库: {len(hist_events)} 条")

# 赛道 1 日样本统计 (用 actual_ret_1d 非空)
track_stats = {}
for e in hist_events:
    t = e.get("track")
    r = e.get("reference", {})
    ret = r.get("actual_ret_1d")
    if t and ret is not None:
        track_stats.setdefault(t, []).append(float(ret))
print("\n赛道 1 日样本:")
for t, arr in track_stats.items():
    avg = sum(arr) / len(arr)
    strong = [e for e in hist_events if e.get("track") == t and e.get("reference", {}).get("actual_ret_1d") is not None
              and e.get("strength", 0) >= 60 and e.get("sentiment") == "正面"]
    sarr = [e["reference"]["actual_ret_1d"] for e in strong]
    s_avg = sum(sarr) / len(sarr) if sarr else None
    print(f"  {t}: n={len(arr)} 均值={avg:+.2f}% | 强正面 n={len(sarr)} 均值={(s_avg if s_avg is not None else 0):+.2f}%")

# ---------- 3. 关键词相似度匹配 ----------
KW = {
    "A股医药": ["创新药", "医药", "BD", "出海", "中报", "药企", "FDA", "集采", "ETF", "CRO", "临床", "GLP", "医保", "百济", "药明"],
    "大消费": ["白酒", "茅台", "五粮液", "消费", "酒价", "批价", "提价", "中秋", "猪", "乳品", "国窖"],
    "恒生科技": ["腾讯", "港股", "恒生", "恒科", "南向", "中概", "互联网", "科网", "阿里", "视频号", "AI", "云"],
    "美股标普医药": ["礼来", "GLP", "减肥药", "医疗", "默沙东", "强生", "XLV", "美股医药", "FDA", "MNC", "药王"],
    "宏观": ["CPI", "美联储", "加息", "美股", "利率", "原油", "油价", "非农", "美债", "通胀", "FOMC"],
}

def match_hist(ev):
    """返回 (match_titles, confidence)"""
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

out_events = []
for s in senti:
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
    out_events.append(ev)

with open(os.path.join(EVENTS, "events-2026-08-12.json"), "w", encoding="utf-8") as f:
    json.dump(out_events, f, ensure_ascii=False, indent=1)
print(f"\n事件库写入 {len(out_events)} 条 (events-2026-08-12.json)")
for e in out_events:
    mt = e["reference"]["match_titles"]
    print(f"  {e['id']} {e['track']} {e['sentiment']}{e['strength']} 匹配{len(mt)}条 置信度{e['reference']['confidence']}")
print("DONE")
