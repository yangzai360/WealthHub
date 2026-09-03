# -*- coding: utf-8 -*-
"""2026-09-03 盘后: DeepSeek 情绪标注 7 条盘后新增新闻（单批 ≤7 规避空响应 §3.60）"""
import json, urllib.request, os, time

BASE = "/Users/jieyang/Documents/WealthHub"
NEWS_PATH = os.path.join(BASE, "data/processed/news/news-2026-09-03.json")
SENT_PATH = os.path.join(BASE, "data/processed/news/sentiment-2026-09-03.json")

with open("/Users/jieyang/.pi/agent/auth.json") as f:
    key = json.load(f)["deepseek"]["key"]

# 已标注标题集合（sentiment 文件现有 27 条）
sent_existing = json.load(open(SENT_PATH, encoding="utf-8"))
labeled_titles = set(s["title"][:50] for s in sent_existing)

all_news = json.load(open(NEWS_PATH, encoding="utf-8"))
# 盘后新增 = 未标注的
news = [n for n in all_news if n["title"][:50] not in labeled_titles]
print(f"待标注 {len(news)} 条（盘后新增，窗口 14:00-20:00）")

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
batch_size = 7
batches = [news[i:i+batch_size] for i in range(0, len(news), batch_size)]
print(f"共 {len(news)} 条, 分 {len(batches)} 批 (每批≤{batch_size})")

for bi, batch in enumerate(batches, 1):
    base_i = (bi - 1) * batch_size
    content = call_ds(build_prompt(batch))
    print(f"=== 批 {bi} DS 原始输出 (前 200 字) ===")
    print(content[:200])
    parsed = parse_labels(content)
    print(f"解析到 {len(parsed)} 条标注")
    for l in parsed:
        labels[int(l["i"]) + base_i] = l

# 汇总：news 字段 + 情绪字段（DeepSeek i 从 1 开始，用 enumerate(news, 1) 对齐）
results = []
for i, n in enumerate(news, 1):
    lab = labels.get(i)
    if lab is None:
        print(f"WARN 未标注: {n['title'][:40]}")
        continue
    item = dict(n)
    item.update({
        "sentiment": lab["sentiment"], "score": lab["score"], "strength": lab["score"],
        "direction": lab["direction"], "volatility": lab["volatility"], "reason": lab["reason"],
    })
    results.append(item)

# 追加到 sentiment 文件
sent_existing.extend(results)
with open(SENT_PATH, "w", encoding="utf-8") as f:
    json.dump(sent_existing, f, ensure_ascii=False, indent=1)
print(f"sentiment-2026-09-03.json 现共 {len(sent_existing)} 条（+{len(results)}）")

# 同步情绪字段回 news JSON
by_title = {s["title"]: s for s in results}
cnt = 0
for n in all_news:
    key = n["title"]
    if key in by_title:
        n["sentiment"] = by_title[key]["sentiment"]
        n["score"] = by_title[key]["score"]
        n["strength"] = by_title[key]["strength"]
        n["direction"] = by_title[key]["direction"]
        n["volatility"] = by_title[key]["volatility"]
        n["reason"] = by_title[key]["reason"]
        cnt += 1
with open(NEWS_PATH, "w", encoding="utf-8") as f:
    json.dump(all_news, f, ensure_ascii=False, indent=1)
print(f"news 同步情绪字段 {cnt} 条")
