# -*- coding: utf-8 -*-
"""2026-10-05 盘后档：DeepSeek 情绪标注（news-close-20261005.json → sentiment-2026-10-05.json）
⚠️ §3.1：max_tokens 必须 8000+（deepseek-v4-flash 深度思考先占输出 token）
⚠️ §3.96：sentiment-<DATE>.json 为 dict {date,window,count,items}，读取须 doc.get('items',[])，写回保留四键
⚠️ 分 5 条一批，逐批调用；content 为空则重试一次（§3.11）
⚠️ §3.103 / §3.112d：逐条写 window 字段（news 与 sentiment 双侧）
⚠️ §3.119c：本档为「混合档」（A股休市 + 港股续市第 2 日已收盘），传导目标逐市场分列：
   A股类 → 10/8（复市首日）；港股类 → 10/5（当日已收盘、可即时定价）；美股类 → 10/2（上一有效收盘，US 10/5 收盘成型于北京 10/6 04:00）
"""
import json, os, re, time, urllib.request
from collections import Counter

BASE = "/Users/jieyang/Documents/WealthHub"
TODAY = "2026-10-05"
NEWS_C = os.path.join(BASE, "data/processed/news/news-close-20261005.json")
NEWS_D = os.path.join(BASE, "data/processed/news/news-2026-10-05.json")
SENT = os.path.join(BASE, "data/processed/news/sentiment-2026-10-05.json")
WIN = "盘后(14:00-20:00)"

key = json.load(open('/Users/jieyang/.pi/agent/auth.json'))['deepseek']['key']
items = json.load(open(NEWS_C, encoding='utf-8'))
if not items:
    raise SystemExit('⚠️ news-close-20261005.json 为空，终止')
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
1) 站在「组合持仓」视角：组合核心赛道为大消费、A股医药、美股标普医药、恒生科技，另有其他/宽基与现金。
2) 区分「个股催化」与「板块级影响」；个股级催化 strength 不得超过 70。
3) 若同一条新闻同时含正反两面，取净方向并降低 confidence。
4) 政策类、业绩类、行业事件类、宏观类须分别考虑其对盈利与估值的作用路径。
5) ⚠️ 本条为「2026-10-05（周一）长假第 5 日盘后（14:00-20:00）」信息，当日为**混合档**：A股休市（10/1-10/7）、**港股正常交易并已于 16:00 收盘（恒生指数 +0.28%、恒生科技 +0.62%）**、美股休市（10/3-10/4 周末、US 10/5 收盘成型于北京 10/6 04:00）。
   传导目标须**逐市场分列**：**港股类事件 → 2026-10-05（当日已收盘、已进入「待消化」口径）；A股类事件 → 2026-10-08（A股复市首日）；美股类事件 → 2026-10-02（美股上一有效收盘，本档无新增）**。
   **港股通（南向）10/1-10/7 全程暂停、10/8 恢复** → 港股定价由外资与本地资金主导、承接变薄。
6) 一切「获批/首次上市/大涨」类表述若无法核验原始获批日与实际收盘，应降级为「未核实」，不得给高强度分。
7) 组合未直接持有港交所上市工具 → 港股行情对组合**不产生当日可实现盈亏**，只进入「待消化」。

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
if os.path.exists(SENT):
    doc = json.load(open(SENT, encoding='utf-8'))
    old = doc.get('items', []) if isinstance(doc, dict) else doc
    old_win = doc.get('window', '') if isinstance(doc, dict) else ''
else:
    old, old_win = [], ''
print(f'既有 sentiment 条目数 = {len(old)}')

new_items = []
for it in items:
    o = labeled.get(it["idx"], {})
    new_items.append({
        "idx": len(old) + it["idx"],
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
missing_win = [x for x in doc['items'] if not x.get('window')]
print('window 覆盖:', doc['count'] - len(missing_win), '/', doc['count'])

news = json.load(open(NEWS_D, encoding='utf-8')) if os.path.exists(NEWS_D) else []
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
missing_win2 = [x for x in news if not x.get('window')]
print('news window 覆盖:', len(news) - len(missing_win2), '/', len(news))

strong_pos = [x for x in new_items if x["direction"] == "利多" and x["strength"] >= 70]
strong_neg = [x for x in new_items if x["direction"] == "利空" and x["strength"] >= 70]
print("方向分布:", dict(Counter(x["direction"] for x in new_items)))
print("赛道分布:", dict(Counter(x["track"] for x in new_items)))
print(f"均值强度 {sum(x['strength'] for x in new_items)/len(new_items):.2f}")
print(f"强正事件(利多且>=70): n={len(strong_pos)} 均值强度 {sum(x['strength'] for x in strong_pos)/max(len(strong_pos),1):.1f}")
print(f"强负事件(利空且>=70): n={len(strong_neg)} 均值强度 {sum(x['strength'] for x in strong_neg)/max(len(strong_neg),1):.1f}")


# 名义净分（强度/10 带符号求和）
def net(its):
    return sum((x['strength'] if x['direction'] == '利多' else -x['strength'] if x['direction'] == '利空' else 0) / 10 for x in its)


print(f"\n名义净情绪 = {net(new_items):.1f}")
by_track = {}
for x in new_items:
    by_track.setdefault(x['track'], []).append(x)
for t, arr in sorted(by_track.items(), key=lambda kv: -net(kv[1])):
    print(f"  [{t:8s}] n={len(arr)} 净分 {net(arr):+.1f} 均值强度 {sum(a['strength'] for a in arr)/len(arr):.1f}")
print("\n逐条:")
for x in new_items:
    print(f"  [{x['track']:8s}] {x['direction']} {x['strength']:>3d} | {x['brief']}")
