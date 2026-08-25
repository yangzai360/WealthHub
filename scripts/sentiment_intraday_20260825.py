# -*- coding: utf-8 -*-
"""2026-08-25 盘中: DeepSeek 情绪标注 8 条盘中新增新闻"""
import json, urllib.request, os, sys, time

BASE = "/Users/jieyang/Documents/WealthHub"
with open("/Users/jieyang/.pi/agent/auth.json") as f:
    key = json.load(f)["deepseek"]["key"]

with open("/tmp/intraday_news_20260825.json", encoding="utf-8") as f:
    news = json.load(f)

prompt = f"""你是A股/港股/美股投资情绪分析师。对以下 {len(news)} 条财经新闻逐条标注情绪。

每条输出 JSON 对象，字段：
- "sentiment": "正面"/"中性"/"负面"
- "score": 0-100 整数（情绪强度，50=中性）
- "direction": "利多"/"利空"/"中性"
- "volatility": "低"/"中"/"高"（预期对相关赛道波动影响）
- "reason": 30字内标注理由（结合持仓赛道：大消费/A股医药/美股标普医药/恒生科技/宏观）

严格输出 JSON 数组，不要任何前缀后缀文字。每条新闻的标题和摘要如下：

{json.dumps([{ "i": i+1, "title": n["title"], "summary": n["summary"]} for i, n in enumerate(news)], ensure_ascii=False, indent=2)}

输出格式：[{{"i":1,"sentiment":"...","score":..,"direction":"...","volatility":"...","reason":"..."}}, ...]
"""

def call_ds(prompt_text, retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            data = {
                "model": "deepseek-v4-flash",
                "messages": [{"role": "user", "content": prompt_text}],
                "max_tokens": 8000,
                "temperature": 0.3,
            }
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions",
                data=json.dumps(data).encode(),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.load(resp)
            content = result["choices"][0]["message"]["content"]
            if not content or not content.strip():
                raise ValueError("empty content")
            return content
        except Exception as e:
            last = e
            time.sleep(2)
    raise last

content = call_ds(prompt)
print("=== DS 原始输出 (前 500 字) ===")
print(content[:500])

start, end = content.find("["), content.rfind("]")
if start == -1 or end == -1:
    print("ERROR: 未找到 JSON 数组")
    sys.exit(1)
try:
    labels = json.loads(content[start:end+1])
except Exception as e:
    print(f"JSON 解析失败: {e}")
    sys.exit(1)

print(f"\n解析到 {len(labels)} 条标注")
by_i = {int(l["i"]): l for l in labels}

results = []
for i, n in enumerate(news, 1):
    l = by_i.get(i)
    if not l:
        print(f"  WARN: 缺 {i}")
        continue
    n["sentiment"] = l["sentiment"]
    n["score"] = int(l["score"])
    n["direction"] = l["direction"]
    n["volatility"] = l["volatility"]
    n["reason"] = l["reason"]
    results.append(n)
    print(f"  [{n['category']}] {n['sentiment']}{n['score']} {n['direction']} 波动{n['volatility']} | {n['title'][:40]}")

# 写回 sentiment 文件（追加到盘前）
sent_path = os.path.join(BASE, "data/processed/news/sentiment-2026-08-25.json")
with open(sent_path, encoding="utf-8") as f:
    sent = json.load(f)
existing_ids = {(n["title"][:40]) for n in sent}
for n in results:
    if n["title"][:40] not in existing_ids:
        sent.append(n)
with open(sent_path, "w", encoding="utf-8") as f:
    json.dump(sent, f, ensure_ascii=False, indent=2)
print(f"\nsentiment-2026-08-25.json 共 {len(sent)} 条 (盘前{len(sent)-len(results)} + 盘中{len(results)})")
