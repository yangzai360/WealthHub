# -*- coding: utf-8 -*-
"""2026-09-16 盘前档情绪标注（DeepSeek v4-flash, max_tokens=8000）
分批标注（每批 7 条），results key 用全局偏移（§3.72 教训）
"""
import json, urllib.request, os

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news')
DATE = '2026-09-16'

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

items = json.load(open(os.path.join(NEWS, f'news-{DATE}.json'), encoding='utf-8'))
print(f'载入 {len(items)} 条新闻')

prompt_head = """你是资深证券分析师。请对下列每条财经新闻做情绪标注，严格只输出 JSON 数组，不要任何解释文字。
每条输出字段：
- idx: 序号(从1开始，沿用输入给出的编号)
- sentiment: "正面"|"中性"|"负面"
- strength: 0-100 整数(情绪强度)
- confidence: 0-100 整数(对A股/港股相关赛道影响的置信度)
- direction: "利多"|"利空"|"中性"
- volatility: "高"|"中"|"低"(预期波动幅度)
- brief: 一句话影响判断(不超过40字)

新闻列表：
"""

BATCH = 7
results = {}
for bi in range(0, len(items), BATCH):
    chunk = items[bi:bi+BATCH]
    prompt = prompt_head
    for j, it in enumerate(chunk, 1):
        prompt += f"{j}. [track={it['track']}] {it['title']}\n"
    data = {"model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8000, "temperature": 0.3}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    content = ''
    for attempt in range(3):
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.load(resp)
        content = result['choices'][0]['message'].get('content', '') or ''
        if content.strip():
            break
        print(f'  批{bi//BATCH+1} 第{attempt+1}次 content 为空，重试')
    s, e = content.find('['), content.rfind(']')
    arr = json.loads(content[s:e+1])
    for o in arr:
        results[bi + int(o['idx'])] = o
    print(f'  批{bi//BATCH+1} 完成 {len(arr)} 条')

out = []
for gi in range(len(items)):
    o = results.get(gi + 1)
    if o is None:
        print(f'  WARN 第 {gi+1} 条未标注')
        continue
    out.append({'idx': gi+1, 'title': items[gi]['title'][:60], 'track': items[gi]['track'],
                'sentiment': o['sentiment'], 'strength': int(o['strength']),
                'confidence': int(o['confidence']), 'direction': o['direction'],
                'volatility': o['volatility'], 'brief': o.get('brief', '')})

with open(os.path.join(NEWS, f'sentiment-{DATE}.json'), 'w', encoding='utf-8') as f:
    json.dump({'date': DATE, 'window': '2026-09-15 18:00 - 2026-09-16 07:30 (盘前)', 'items': out},
              f, ensure_ascii=False, indent=1)

# 同步回 news JSON（统一 title[:60] 截断口径，§3.82 教训）
for it in items:
    for o in out:
        if it['title'][:60] == o['title']:
            it['sentiment'] = o['sentiment']
            it['score'] = o['strength']
            it['strength'] = o['strength']
            it['direction'] = o['direction']
            it['volatility'] = o['volatility']
            it['brief'] = o['brief']
with open(os.path.join(NEWS, f'news-{DATE}.json'), 'w', encoding='utf-8') as f:
    json.dump(items, f, ensure_ascii=False, indent=1)

for o in out:
    print(f"  {o['idx']:2d} {o['track']:8s} {o['sentiment']} {o['strength']:3d}/{o['confidence']:3d} {o['direction']} {o['volatility']} | {o['brief']}")
pos = sum(1 for o in out if o['direction'] == '利多')
neg = sum(1 for o in out if o['direction'] == '利空')
neu = sum(1 for o in out if o['direction'] == '中性')
avg = sum(o['strength'] for o in out) / len(out)
print(f'\n共 {len(out)} 条, 利多 {pos} / 利空 {neg} / 中性 {neu}, 均值强度 {avg:.1f}')
