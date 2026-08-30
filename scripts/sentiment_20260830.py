# -*- coding: utf-8 -*-
"""周日(8/30)盘后档:DeepSeek 情绪标注周末新闻(与内置情绪交叉校验)"""
import json, urllib.request, re, sys

NEWS_PATH = '/Users/jieyang/Documents/WealthHub/data/processed/news/news-2026-08-30.json'
SENT_PATH = '/Users/jieyang/Documents/WealthHub/data/processed/news/sentiment-2026-08-30.json'

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
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.load(resp)
    return result['choices'][0]['message']['content']

# 分批标注(每批 7 条)
BATCH = 7
all_results = []
for i in range(0, len(news), BATCH):
    batch = news[i:i+BATCH]
    items = []
    for n in batch:
        items.append({"title": n['title'][:150], "track": n['track'], "category": n['category']})
    prompt = f"""你是A股/港股/美股投资情绪分析师。对以下 {len(batch)} 条财经新闻逐一标注情绪。

要求:
1. sentiment: 正面/中性/负面
2. score: 情绪分 0-100(50=中性,>60偏多,<40偏空)
3. strength: 对持仓赛道影响强度 0-100
4. direction: 利多/利空/中性
5. volatility: 预期波动 高/中/低
6. 单条评论 ≤30 字

输出 JSON 数组,每个元素对应一条新闻,按原顺序:
[
 {{"sentiment": "...", "score": 0, "strength": 0, "direction": "...", "volatility": "...", "comment": "..."}}
]

新闻列表:
{json.dumps(items, ensure_ascii=False)}"""
    content = call_deepseek(prompt)
    # 提取 JSON 数组
    s, e = content.find('['), content.rfind(']')
    arr = json.loads(content[s:e+1])
    all_results.extend(arr)
    print(f'批次 {i//BATCH+1} 完成,标注 {len(arr)} 条')

# 写 sentiment 文件(含标题便于回补)
sentiments = []
for n, r in zip(news, all_results):
    sentiments.append({
        "date": "2026-08-30",
        "track": n['track'],
        "title": n['title'],
        "sentiment": r['sentiment'],
        "score": r['score'],
        "strength": r['strength'],
        "direction": r['direction'],
        "volatility": r['volatility'],
        "comment": r['comment'],
    })
with open(SENT_PATH, 'w', encoding='utf-8') as f:
    json.dump(sentiments, f, ensure_ascii=False, indent=1)
print(f'sentiment 写入 {len(sentiments)} 条 -> {SENT_PATH}')

# 同步回 news JSON
with open(NEWS_PATH, encoding='utf-8') as f:
    news2 = json.load(f)
for n in news2:
    for s in sentiments:
        if s['title'] == n['title']:
            n['sentiment'] = s['sentiment']
            n['score'] = s['score']
            n['strength'] = s['strength']
            n['direction'] = s['direction']
            n['volatility'] = s['volatility']
            n['comment'] = s['comment']
            break
with open(NEWS_PATH, 'w', encoding='utf-8') as f:
    json.dump(news2, f, ensure_ascii=False, indent=1)
print('news JSON 情绪字段已同步')
