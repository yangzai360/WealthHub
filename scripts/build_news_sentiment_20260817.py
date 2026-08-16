# -*- coding: utf-8 -*-
"""2026-08-17 盘前 12 条新闻情绪标注（DeepSeek v4-flash, max_tokens=8000, 空响应重试1次）"""
import json, os, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS_FILE = os.path.join(BASE, 'data/processed/news/news-2026-08-17.json')
OUT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-17.json')

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

with open(NEWS_FILE, encoding='utf-8') as f:
    news = json.load(f)

prompt = f"""你是 A股医药/消费/港股科技/美股医疗 ETF 投研情绪分析师。请对以下 {len(news)} 条财经新闻逐条输出情绪标注，输出为 JSON 数组，每个元素包含字段：
- title: 新闻标题（原文复制）
- sentiment: "正面"/"中性"/"负面"
- score: 0-100 的乐观/悲观分（50=中性，>50偏乐观，<50偏悲观）
- strength: 0-100 的情绪强度（影响显著性，60+为高强度）
- direction: "利多"/"利空"/"中性"
- volatility: "高"/"中"/"低"（对相关板块的预期波动影响）
- reason: 一句话理由

要求：
1. 结合新闻对以下赛道的影响判断：大消费（白酒/消费）、A股医药（创新药/医药）、美股标普医药（美股医药股/QDII医药）、恒生科技（港股科技/AI/中概）
2. 只输出 JSON 数组本身，不要任何前后缀文字、不要 markdown 代码块。

新闻列表：
{json.dumps(news, ensure_ascii=False, indent=1)}"""

def call(prompt):
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        result = json.load(resp)
    return result['choices'][0]['message']['content']

content = call(prompt)
if not content or content.strip() == '':
    print('WARN 首次返回空 content, 重试...')
    import time; time.sleep(3)
    content = call(prompt)

# 截取 JSON 数组
start = content.find('[')
end = content.rfind(']')
if start == -1 or end == -1:
    print('ERROR 无法定位 JSON:', content[:500])
    raise SystemExit(1)
arr = json.loads(content[start:end+1])
print(f'情绪标注成功 {len(arr)} 条')
for a in arr:
    print(f"  {a['sentiment']}/{a['strength']} {a['title'][:30]}...")

# 按 news 顺序对齐
by_title = {a['title']: a for a in arr}
out = []
for n in news:
    a = by_title.get(n['title'])
    if not a:
        print(f'  WARN 未匹配: {n["title"][:30]}')
        a = {'sentiment': '中性', 'score': 50, 'strength': 50, 'direction': '中性', 'volatility': '中', 'reason': '自动占位'}
    out.append({**n, 'sentiment': a['sentiment'], 'score': a['score'], 'strength': a['strength'],
                'direction': a['direction'], 'volatility': a['volatility'], 'reason': a['reason']})

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f'\nDONE -> sentiment-2026-08-17.json')
