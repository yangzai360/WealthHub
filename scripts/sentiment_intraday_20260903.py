# -*- coding: utf-8 -*-
"""2026-09-03 盘中: DeepSeek 情绪标注 8 条盘中新增新闻 (分2批, 每批≤7 规避空响应)"""
import json, urllib.request, os, sys, time

BASE = "/Users/jieyang/Documents/WealthHub"
with open("/Users/jieyang/.pi/agent/auth.json") as f:
    key = json.load(f)["deepseek"]["key"]

with open("/tmp/intraday_news_20260903.json", encoding="utf-8") as f:
    news = json.load(f)

def call_ds(prompt_text, retries=4):
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
            time.sleep(5)
    raise last

def parse_labels(content):
    # 剥离可能的代码块围栏
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3]
    start, end = content.find("["), content.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("未找到 JSON 数组")
    return json.loads(content[start:end+1])

def build_prompt(batch):
    return f"""你是A股/港股/美股投资情绪分析师。对以下 {len(batch)} 条财经新闻逐条标注情绪。

每条输出 JSON 对象，字段：
- "sentiment": "正面"/"中性"/"负面"
- "score": 0-100 整数（情绪强度，50=中性）
- "direction": "利多"/"利空"/"中性"
- "volatility": "低"/"中"/"高"（预期对相关赛道波动影响）
- "reason": 30字内标注理由（结合持仓赛道：大消费/A股医药/美股标普医药/恒生科技/宏观）

严格输出 JSON 数组，不要任何前缀后缀文字。每条新闻的标题和摘要如下：

{json.dumps([{ "i": i+1, "title": n["title"], "summary": n["summary"]} for i, n in enumerate(batch)], ensure_ascii=False, indent=2)}

输出格式：[{{"i":1,"sentiment":"...","score":..,"direction":"...","volatility":"...","reason":"..."}}, ...]
"""

labels = {}
# 分批处理: 每批 ≤7
batch_size = 7
batches = [news[i:i+batch_size] for i in range(0, len(news), batch_size)]
print(f"共 {len(news)} 条, 分 {len(batches)} 批 (每批≤{batch_size})")

for bi, batch in enumerate(batches, 1):
    base_i = (bi - 1) * batch_size
    content = call_ds(build_prompt(batch))
    print(f"=== 批 {bi} DS 原始输出 (前 300 字) ===")
    print(content[:300])
    parsed = parse_labels(content)
    print(f"解析到 {len(parsed)} 条标注")
    for l in parsed:
        labels[int(l["i"]) + base_i] = l
    if bi < len(batches):
        time.sleep(2)

print(f"\n共解析 {len(labels)} 条")
by_i = labels

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
sent_path = os.path.join(BASE, "data/processed/news/sentiment-2026-09-03.json")
with open(sent_path, encoding="utf-8") as f:
    sent = json.load(f)
existing_ids = {(n["title"][:40]) for n in sent}
added = 0
for n in results:
    if n["title"][:40] not in existing_ids:
        sent.append(n)
        added += 1
with open(sent_path, "w", encoding="utf-8") as f:
    json.dump(sent, f, ensure_ascii=False, indent=2)
print(f"\nsentiment-2026-09-03.json 共 {len(sent)} 条 (盘前{len(sent)-added} + 盘中{added})")
