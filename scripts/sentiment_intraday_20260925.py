# -*- coding: utf-8 -*-
"""2026-09-25 盘中档：DeepSeek 情绪标注（news-intraday-20260925.json → sentiment-2026-09-25.json）
⚠️ §3.1：max_tokens 必须 8000+（deepseek-v4-flash 深度思考先占输出 token）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,items}，读取须 doc.get('items',[])，写回保留
⚠️ §3.103：window 字段双写（news + sentiment）
⚠️ 分 5 条一批；content 为空重试一次
"""
import json, os, re, time, urllib.request

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_I = os.path.join(BASE, "data/processed/news/news-intraday-20260925.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-09-25.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-09-25.json")
TODAY = "2026-09-25"
WIN = "盘中(07:30-13:30)"

key = json.load(open('/Users/jieyang/.pi/agent/auth.json'))['deepseek']['key']
items = json.load(open(NEWS_I, encoding='utf-8'))
if len(items) == 0:
    raise SystemExit('⚠️ 待标注 0 条，终止')
print(f"待标注 {len(items)} 条")

PROMPT = """你是A股/港股/美股医药与消费行业的资深卖方分析师。对下列新闻逐条做情绪标注，只输出 JSON 数组，不要任何解释。

每条输出字段：
- idx: 输入编号
- sentiment: "正面"|"中性"|"负面"
- strength: 0-100 整数（情绪强度）
- confidence: 0-100 整数（对该标注的置信度）
- direction: "利多"|"中性"|"利空"
- volatility: "低"|"中"|"高"（对相关赛道未来3-5日波动率的预期）
- brief: 不超过18字的要点

判定要求：
1) 站在「组合持仓」视角：组合核心赛道为大消费、A股医药、美股标普医药、恒生科技。
2) 区分「个股催化」与「板块级影响」；个股级催化 strength 不得超过 70。
3) 若同一条新闻同时含正反两面，取净方向并降低 confidence。
4) 政策类、业绩类、行业事件类、宏观类须分别考虑其对盈利与估值的作用路径。
5) 注意：2026-09-25 为A股中秋休市日、港股正常交易，点评时应考虑流动性缺位对价格弹性的影响。

新闻列表：
"""


def call(batch):
    body = PROMPT + json.dumps(
        [{"idx": b["idx"], "track": b["track"], "category": b["category"],
          "title": b["title"], "summary": b["summary"]} for b in batch],
        ensure_ascii=False, indent=1)
    data = {"model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": body}],
            "max_tokens": 8000, "temperature": 0.3}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                                data=json.dumps(data).encode(),
                                headers={"Authorization": f"Bearer {key}",
                                         "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        r = json.load(resp)
    return r['choices'][0]['message'].get('content') or ''


for i, it in enumerate(items):
    it["idx"] = i + 1

labeled = {}
B = 5
for s in range(0, len(items), B):
    batch = items[s:s + B]
    txt = ""
    for attempt in range(2):
        try:
            txt = call(batch)
        except Exception as e:
            print(f"  批 {s//B+1} 调用异常: {e}")
            txt = ""
        if txt.strip():
            break
        print(f"  批 {s//B+1} 空响应，重试一次")
        time.sleep(2)
    m = re.search(r"\[[\s\S]*\]", txt)
    if not m:
        print(f"⚠️ 批 {s//B+1} 无 JSON，退化为原标签")
        for b in batch:
            labeled[b["idx"]] = {k: b[k] for k in ("sentiment", "score", "direction", "volatility", "brief")}
        continue
    try:
        arr = json.loads(m.group(0))
    except Exception as e:
        print(f"⚠️ 批 {s//B+1} JSON 解析失败: {e}")
        for b in batch:
            labeled[b["idx"]] = {k: b[k] for k in ("sentiment", "score", "direction", "volatility", "brief")}
        continue
    for o in arr:
        labeled[int(o["idx"])] = o
    print(f"  批 {s//B+1} 完成 {len(arr)} 条")

# ---------- 写回 ----------
doc = json.load(open(SENT, encoding='utf-8'))
if not isinstance(doc, dict):
    doc = {"date": TODAY, "window": WIN, "items": doc}
old = doc.get('items', [])
old_win = doc.get('window', '')
base_idx = max([o.get('idx', 0) for o in old], default=0)

new_items = []
for it in items:
    o = labeled.get(it["idx"], {})
    new_items.append({
        "idx": base_idx + it["idx"],
        "title": it["title"][:60],
        "track": it["track"],
        "window": WIN,
        "sentiment": o.get("sentiment", it["sentiment"]),
        "strength": int(o.get("strength", o.get("score", it["score"]))),
        "confidence": int(o.get("confidence", 90)),
        "direction": o.get("direction", it["direction"]),
        "volatility": o.get("volatility", it["volatility"]),
        "brief": o.get("brief", it["brief"])[:22],
    })

doc = {"date": TODAY,
       "window": (old_win + " + " + WIN) if old_win else WIN,
       "count": len(old) + len(new_items),
       "items": old + new_items}
json.dump(doc, open(SENT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nsentiment-{TODAY}.json: {len(old)} -> {doc['count']} 条")

# news-<DATE>.json 追加（保留原字段，补 sentiment 结论 + window 双写）
news = json.load(open(NEWS_D, encoding='utf-8'))
for it, ni in zip(items, new_items):
    it2 = dict(it)
    it2["window"] = WIN
    it2["sentiment"] = ni["sentiment"]
    it2["score"] = ni["strength"]
    it2["strength"] = ni["strength"]
    it2["confidence"] = ni["confidence"]
    it2["direction"] = ni["direction"]
    it2["volatility"] = ni["volatility"]
    it2["brief"] = ni["brief"]
    news.append(it2)
json.dump(news, open(NEWS_D, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"news-{TODAY}.json: {len(news)} 条")

from collections import Counter
strong_pos = [x for x in new_items if x["direction"] == "利多" and x["strength"] >= 70]
strong_neg = [x for x in new_items if x["direction"] == "利空" and x["strength"] >= 70]
print("方向分布:", dict(Counter(x["direction"] for x in new_items)))
print(f"强正事件(利多且>=70): n={len(strong_pos)} 均值强度 {sum(x['strength'] for x in strong_pos)/max(len(strong_pos),1):.1f}")
print(f"强负事件(利空且>=70): n={len(strong_neg)} 均值强度 {sum(x['strength'] for x in strong_neg)/max(len(strong_neg),1):.1f}")
print("赛道×方向:")
for tr in sorted(set(x["track"] for x in new_items)):
    sub = [x for x in new_items if x["track"] == tr]
    net = sum((x["strength"] if x["direction"] == "利多" else -x["strength"] if x["direction"] == "利空" else 0) for x in sub)
    print(f"  {tr:12s} n={len(sub):2d} 均值强度 {sum(x['strength'] for x in sub)/len(sub):5.1f} 净分 {net:+6.1f}")
