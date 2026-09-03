# -*- coding: utf-8 -*-
"""盘前档 2026-09-03:DeepSeek 情绪标注(19条) 重试增强版——批次 7 条 + 每批最多 4 次重试 + 代码块剥离"""
import json, urllib.request, time

NEWS_PATH = '/Users/jieyang/Documents/WealthHub/data/processed/news/news-2026-09-03.json'
SENT_PATH = '/Users/jieyang/Documents/WealthHub/data/processed/news/sentiment-2026-09-03.json'

with open(NEWS_PATH, encoding='utf-8') as f:
    news = json.load(f)

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

def call_deepseek(prompt):
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as resp:
        result = json.load(resp)
    return result['choices'][0]['message']['content']

def parse(content):
    if not content:
        return None
    s = content.find('[')
    e = content.rfind(']')
    if s == -1 or e == -1 or e <= s:
        return None
    return json.loads(content[s:e+1])

BATCH = 7
all_results = []
for i in range(0, len(news), BATCH):
    batch = news[i:i+BATCH]
    items = [{"title": n['title'][:200], "track": n['track'], "category": n['category']} for n in batch]
    prompt = f"""你是A股/港股/美股投资情绪分析师。对以下 {len(batch)} 条财经新闻逐一标注情绪。

要求:
1. sentiment: 正面/中性/负面
2. score: 情绪分 0-100(50=中性,>60偏多,<40偏空)
3. strength: 对持仓赛道影响强度 0-100
4. direction: 利多/利空/中性
5. volatility: 预期波动 高/中/低
6. 单条评论 ≤30 字

只输出 JSON 数组,不要任何其他文字,每个元素对应一条新闻,按原顺序:
[
 {{"sentiment": "...", "score": 0, "strength": 0, "direction": "...", "volatility": "...", "comment": "..."}}
]

新闻列表:
{json.dumps(items, ensure_ascii=False)}"""
    arr = None
    for attempt in range(4):
        try:
            content = call_deepseek(prompt)
            arr = parse(content)
            if arr is not None and len(arr) == len(batch):
                break
            print(f'  批次 {i//BATCH+1} 第{attempt+1}次解析失败, 重试...')
        except Exception as e:
            print(f'  批次 {i//BATCH+1} 第{attempt+1}次异常: {e}, 重试...')
        time.sleep(5)
    if arr is None or len(arr) != len(batch):
        raise RuntimeError(f'批次 {i//BATCH+1} 连续失败, 放弃')
    all_results.extend(arr)
    print(f'批次 {i//BATCH+1} 完成,标注 {len(arr)} 条')

assert len(all_results) == len(news), f"数量不一致: {len(all_results)} vs {len(news)}"
out = []
for n, r in zip(news, all_results):
    out.append({"date": "2026-09-03", "track": n["track"], "title": n["title"],
                "sentiment": r["sentiment"], "score": r["score"], "strength": r["strength"],
                "direction": r["direction"], "volatility": r["volatility"], "comment": r["comment"]})
with open(SENT_PATH, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f'sentiment-2026-09-03.json 写入 {len(out)} 条')
for s in out:
    print(f"  [{s['track']}] {s['sentiment']} {s['score']}/{s['strength']} {s['direction']} {s['volatility']} | {s['title'][:36]}...")
