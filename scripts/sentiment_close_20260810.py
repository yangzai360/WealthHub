#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘后情绪分析 + 8/10 事件库当日回填 (2026-08-10 20:00 档)
1. DeepSeek 对 news-2026-08-10.json 中缺失情绪字段的盘后新闻(N018-N023)做情绪标注
2. 将盘后新闻并入 events-2026-08-10.json 并回填当日实际走势(actual_ret_1d)
"""
import json, os, time, urllib.request

BASE = "/Users/jieyang/Documents/WealthHub"
NW = os.path.join(BASE, "data/processed/news")
EV = os.path.join(BASE, "data/processed/events")

with open("/Users/jieyang/.pi/agent/auth.json") as f:
    KEY = json.load(f)["deepseek"]["key"]

def ds_analyze(news_items):
    """DeepSeek 批量情绪标注, 返回 id -> {sentiment, strength, impact_direction, expected_volatility, reason}"""
    prompt = (
        "你是A股/港股/美股医药与消费投研分析助手。以下是6条2026-08-10的财经新闻，"
        "请逐条给出情绪分析，输出严格JSON数组，每项字段:\n"
        "{\"id\":\"新闻ID\",\"sentiment\":\"正面|中性|负面\",\"strength\":0-100整数,"
        "\"impact_direction\":\"利多|利空|中性\",\"expected_volatility\":\"高|中|低\","
        "\"reason\":\"一句话理由(中文)\"}\n\n"
        "要求: 情绪强度0-100(正面利多>=60为强, 负面利空>=60为强); 评估对持仓四大赛道"
        "(A股医药/大消费/美股标普医药/恒生科技)的影响方向与预期波动幅度。\n\n"
        + json.dumps(news_items, ensure_ascii=False)
    )
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.load(resp)
            content = result["choices"][0]["message"]["content"]
            if not content or not content.strip():
                print(f"DeepSeek 第{attempt+1}次返回空 content, 重试...")
                time.sleep(2)
                continue
            # 提取 JSON
            start, end = content.find("["), content.rfind("]")
            if start == -1 or end == -1:
                raise ValueError("响应中未找到JSON数组")
            arr = json.loads(content[start:end+1])
            return {item["id"]: item for item in arr}
        except Exception as e:
            print(f"DeepSeek 第{attempt+1}次失败: {e}")
            time.sleep(3)
    return {}

# ---------- 1. 情绪标注 ----------
news_path = os.path.join(NW, "news-2026-08-10.json")
with open(news_path, encoding="utf-8") as f:
    news = json.load(f)
pending = [n for n in news if not n.get("sentiment")]
print(f"待情绪标注: {len(pending)} 条")
if pending:
    analyzed = ds_analyze([{k: n[k] for k in ("id", "title", "summary", "track")} for n in pending])
    for n in pending:
        a = analyzed.get(n["id"])
        if a:
            n["sentiment"] = a.get("sentiment", "")
            n["strength"] = a.get("strength")
            n["impact_direction"] = a.get("impact_direction", "")
            n["expected_volatility"] = a.get("expected_volatility", "")
            n["reason"] = a.get("reason", "")
            print(f"  {n['id']} {n['title'][:20]}... -> {n['sentiment']} {n['strength']}")
        else:
            print(f"  {n['id']} 标注失败")
    with open(news_path, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=1)
    print(f"[news] 情绪标注完成, 共 {len(news)} 条")
else:
    print("无待标注新闻")

# ---------- 2. 事件库: 将盘后新闻并入 events-2026-08-10.json + 当日回填 ----------
events_path = os.path.join(EV, "events-2026-08-10.json")
with open(events_path, encoding="utf-8") as f:
    events = json.load(f)
existing_ids = {e["id"] for e in events}

# 8/10 当日实际走势 (收盘)
TRACK_RET = {
    "A股医药": 1.63,
    "大消费": 2.50,
    "恒生科技": 1.37,
    "宏观": 0.67,
    "美股标普医药": None,
}

added = 0
for n in news:
    if n["id"] in existing_ids:
        # 已有事件: 回填当日实际走势
        for e in events:
            if e["id"] == n["id"]:
                ref = e.get("reference", {})
                if ref.get("actual_ret_1d") is None:
                    ret = TRACK_RET.get(e.get("track", "宏观"))
                    if ret is not None:
                        ref["actual_ret_1d"] = ret
                        ref["actual_date"] = "2026-08-10"
                break
        continue
    # 新事件
    ev = {
        "id": n["id"],
        "date": n.get("date", "2026-08-10"),
        "track": n.get("track", "宏观"),
        "category": n.get("category", "行业事件类"),
        "title": n["title"],
        "summary": n.get("summary", ""),
        "source": n.get("source", "WebSearch"),
        "source_url": n.get("source_url", ""),
        "sentiment": n.get("sentiment", ""),
        "strength": n.get("strength"),
        "impact_direction": n.get("impact_direction", ""),
        "expected_volatility": n.get("expected_volatility", ""),
        "reason": n.get("reason", ""),
        "reference": {
            "ret_3d": None, "ret_5d": None, "ret_10d": None,
            "max_vol": None, "confidence": None,
            "actual_ret_1d": TRACK_RET.get(n.get("track", "宏观")),
            "actual_date": "2026-08-10" if TRACK_RET.get(n.get("track", "宏观")) is not None else None,
        },
    }
    events.append(ev)
    existing_ids.add(ev["id"])
    added += 1

with open(events_path, "w", encoding="utf-8") as f:
    json.dump(events, f, ensure_ascii=False, indent=1)
print(f"[events] 新增 {added} 条, 当前共 {len(events)} 条")

# 统计
filled = sum(1 for e in events if (e.get("reference") or {}).get("actual_ret_1d") is not None)
print(f"[events] 已回填当日走势 {filled}/{len(events)} 条")
