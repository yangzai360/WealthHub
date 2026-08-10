#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正 news-2026-08-10.json 中盘前 10 条情绪字段为盘前归档值(sentiment-2026-08-10.json)"""
import json, os

BASE = "/Users/jieyang/Documents/WealthHub"
NW = os.path.join(BASE, "data/processed/news")

with open(os.path.join(NW, "sentiment-2026-08-10.json"), encoding="utf-8") as f:
    pre = json.load(f)
pre_map = {p["id"]: p for p in pre}

with open(os.path.join(NW, "news-2026-08-10.json"), encoding="utf-8") as f:
    news = json.load(f)

fixed = 0
for n in news:
    if n["id"] in pre_map:
        p = pre_map[n["id"]]
        if n.get("sentiment") != p.get("sentiment") or n.get("strength") != p.get("strength"):
            n["sentiment"] = p["sentiment"]
            n["strength"] = p["strength"]
            n["impact_direction"] = p["impact_direction"]
            n["expected_volatility"] = p["expected_volatility"]
            n["reason"] = p["reason"]
            fixed += 1
with open(os.path.join(NW, "news-2026-08-10.json"), "w", encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
print(f"修正 {fixed} 条盘前情绪字段")
for n in news:
    print(f"  {n['id']} {n['sentiment']} {n['strength']}")
