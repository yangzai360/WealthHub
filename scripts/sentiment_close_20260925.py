# -*- coding: utf-8 -*-
"""2026-09-25 盘后档：DeepSeek 情绪标注（news-close-<TODAY>.json → 合并进 sentiment-<TODAY>.json）
⚠️ §3.1：max_tokens 必须 8000+（deepseek-v4-flash 深度思考先占输出 token）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])，写回保留
⚠️ §3.103：window 字段双写（news + sentiment）
⚠️ §3.106/§3.107：写盘路径一律由 TODAY 变量推导，禁止硬编码日期字符串
"""
import json, os, re, time, urllib.request

BASE = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-09-25"
DS = TODAY.replace("-", "")
NEWS_C = os.path.join(BASE, f"data/processed/news/news-close-{DS}.json")
NEWS_D = os.path.join(BASE, f"data/processed/news/news-{TODAY}.json")
SENT = os.path.join(BASE, f"data/processed/news/sentiment-{TODAY}.json")
WIN = "盘后(14:00-20:00)"

key = json.load(open('/Users/jieyang/.pi/agent/auth.json'))['deepseek']['key']
items = json.load(open(NEWS_C, encoding='utf-8'))
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
5) 背景：2026-09-25 为A股中秋休市日、港股正常交易（恒生指数 −1.01%、恒生科技 −1.13%），港股通（南向）自 9/25 起暂停至 10/8 恢复；A股 9/28 复市、9/28-9/30 为本年度最后 3 个连续交易日。
6) 注意区分「厂商自述口径」与「渠道/第三方口径」的矛盾数据，此类条目应降低 confidence。

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
            print(f"  批 {s//B+1} 第{attempt+1}次异常 {e}")
            txt = ""
        if txt.strip():
            break
        print(f"  批 {s//B+1} 第{attempt+1}次空响应，重试")
        time.sleep(3)
    m = re.search(r'\[.*\]', txt, re.S)
    if not m:
        raise SystemExit(f"⚠️ 批 {s//B+1} 未取到 JSON 数组，终止（避免静默丢标注）\n原始: {txt[:400]}")
    arr = json.loads(m.group(0))
    for o in arr:
        labeled[int(o["idx"])] = o
    print(f"  批 {s//B+1}/{(len(items)+B-1)//B} 完成 {len(arr)} 条")

missing = [it["idx"] for it in items if it["idx"] not in labeled]
if missing:
    raise SystemExit(f"⚠️ 缺标注 idx={missing}，终止")

new_items = []
for it in items:
    o = labeled[it["idx"]]
    new_items.append({
        "idx": it["idx"],
        "title": it["title"][:60],
        "track": it["track"],
        "window": WIN,
        "sentiment": o.get("sentiment", it["sentiment"]),
        "strength": int(o.get("strength", o.get("score", it["score"]))),
        "confidence": int(o.get("confidence", 90)),
        "direction": o.get("direction", it["direction"]),
        "volatility": o.get("volatility", it["volatility"]),
        "brief": str(o.get("brief", it["brief"]))[:24],
    })

# ---- sentiment-<TODAY>.json：追加 ----
doc = json.load(open(SENT, encoding='utf-8'))
old = doc.get('items', [])
old_win = doc.get('window', '')
doc = {"date": TODAY,
       "window": (old_win + " + " + WIN) if old_win else WIN,
       "count": len(old) + len(new_items),
       "items": old + new_items}
json.dump(doc, open(SENT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nsentiment-{TODAY}.json: {len(old)} -> {doc['count']} 条")

# ---- news-<TODAY>.json：追加（window 双写 + 情绪结论） ----
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
