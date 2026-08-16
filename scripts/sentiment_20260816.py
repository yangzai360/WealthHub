#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周末新闻情绪标注：DeepSeek v4-flash，max_tokens=8000，重试逻辑"""
import json, re, sys, time, urllib.request

NEWS_PATH = 'data/processed/news/news-2026-08-16.json'
SENT_PATH = 'data/processed/news/sentiment-2026-08-16.json'

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

with open(NEWS_PATH, encoding='utf-8-sig') as f:
    news = json.load(f)

items = []
for n in news:
    items.append({"id": n["id"], "title": n["title"]})

prompt = f"""你是 A股/港股/美股医药与消费板块的资深投研分析师。请对以下 {len(items)} 条财经新闻逐条做情绪标注。

输出要求：严格输出一个 JSON 数组，每项对应一条新闻，字段：
- "id": 新闻 id
- "sentiment": "正面"/"中性"/"负面"
- "score": 0-100 的整数情绪强度分（越高越正面）
- "strength": 0-100 的整数影响强度分（影响越大越高）
- "direction": "利多"/"中性"/"利空"（对 A股/港股/美股医药、消费赛道的持仓影响方向）
- "volatility": "低"/"中"/"高"（对持仓赛道预期的波动幅度）
- "reason": 一句话理由（30 字内）

规则：
- 仅基于新闻内容判断，不臆测；
- 影响方向要结合当前市场环境（美联储加息预期、日本加息风险、白酒行业调整、创新药出海周期）；
- 宏观利空（如美股数据差、日本加息、地缘风险）对成长/QDII 赛道偏负面；
- 白酒批价企稳/提价对消费偏正面，但中报利润下滑偏负面；
- 创新药 BD 出海、业绩超预期对医药偏正面。

新闻列表：
{json.dumps(items, ensure_ascii=False)}"""

def call_deepseek(prompt):
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.load(resp)
    content = result['choices'][0]['message']['content']
    if not content:
        raise ValueError("content is empty")
    return content

content = None
for attempt in range(3):
    try:
        content = call_deepseek(prompt)
        break
    except Exception as e:
        print(f"attempt {attempt+1} failed: {e}", file=sys.stderr)
        time.sleep(5)

if content is None:
    print("FATAL: DeepSeek call failed after retries", file=sys.stderr)
    sys.exit(1)

# 截取 JSON 数组部分
start, end = content.find("["), content.rfind("]")
if start == -1 or end == -1:
    print("FATAL: no JSON array in response", file=sys.stderr)
    print(content[:500], file=sys.stderr)
    sys.exit(1)
result = json.loads(content[start:end+1])
print(f"标注完成: {len(result)} 条")

# 回写 news JSON
id2sent = {r["id"]: r for r in result}
for n in news:
    r = id2sent.get(n["id"])
    if r:
        n["sentiment"] = r.get("sentiment", n.get("sentiment"))
        n["score"] = r.get("score")
        n["strength"] = r.get("strength")
        n["direction"] = r.get("direction")
        n["volatility"] = r.get("volatility")
        n["reason"] = r.get("reason", "")

with open(NEWS_PATH, 'w', encoding='utf-8') as f:
    json.dump(news, f, ensure_ascii=False, indent=1)
# 写 sentiment 文件
with open(SENT_PATH, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print("已写回 news JSON + sentiment JSON")
for r in result:
    print(r["id"], r["sentiment"], r.get("score"), r.get("strength"), r.get("direction"), r.get("volatility"))
