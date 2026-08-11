# -*- coding: utf-8 -*-
"""补标盘中 10 条(N015-024)情绪，追加进 sentiment 并同步 news JSON"""
import json, os, urllib.request, time

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news/news-2026-08-11.json')
SENT = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-11.json')

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

news = json.load(open(NEWS))
sent = json.load(open(SENT))
target_ids = {f'N20260811-{i:03d}' for i in range(15, 25)}
target = [x for x in news if x['id'] in target_ids]

prompt = """你是财经新闻情绪分析器。对以下新闻逐条输出 JSON 数组，每条含字段：
id, sentiment(正面/中性/负面), strength(0-100整数), impact_direction(利多/利空/中性), expected_volatility(低/中/高), reason(30字内中文理由)
输出格式：只输出 JSON 数组，不要其他文字。

新闻列表：
"""
for x in target:
    prompt += f"\n[{x['id']}] 赛道={x['track']} 分类={x['category']}\n标题：{x['title']}\n摘要：{x['summary'][:200]}\n"

def call_ds(p):
    data = {"model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": p}],
            "max_tokens": 8000, "temperature": 0.3}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        r = json.load(resp)
    return r['choices'][0]['message']['content']

content = None
for attempt in range(3):
    try:
        content = call_ds(prompt)
        if content and content.strip():
            break
        time.sleep(3)
    except Exception as e:
        print(f'  attempt {attempt+1} fail: {str(e)[:100]}')
        time.sleep(3)
if not content:
    raise SystemExit('DeepSeek 3 次重试失败')

content = content.strip()
if content.startswith('```'):
    content = content.strip('`')
    if content.startswith('json'):
        content = content[4:]
arr = json.loads(content[content.find('['):content.rfind(']')+1])
print('标注', len(arr), '条')

by_id = {x['id']: x for x in arr}
sent_ids = {x['id'] for x in sent}
for x in target:
    if x['id'] in by_id and x['id'] not in sent_ids:
        a = by_id[x['id']]
        sent.append({'id': x['id'], 'track': x['track'], 'category': x['category'], 'title': x['title'],
                     'source_url': x['source_url'], 'sentiment': a['sentiment'], 'strength': a['strength'],
                     'impact_direction': a['impact_direction'], 'expected_volatility': a['expected_volatility'],
                     'reason': a['reason']})
json.dump(sent, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('sentiment total:', len(sent))

sent_by_id = {x['id']: x for x in sent}
for n in news:
    if n['id'] in sent_by_id:
        s = sent_by_id[n['id']]
        n['sentiment'] = s['sentiment']; n['strength'] = s['strength']
        n['impact_direction'] = s['impact_direction']; n['expected_volatility'] = s['expected_volatility']
        n['reason'] = s['reason']
json.dump(news, open(NEWS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('news 情绪同步完成，total', len(news))
