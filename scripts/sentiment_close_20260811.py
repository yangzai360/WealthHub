# -*- coding: utf-8 -*-
"""DeepSeek 情绪标注：盘中 10 条(占位) + 盘后 9 条，重标后合并回 sentiment/news JSON"""
import json, os, urllib.request, time

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news/news-2026-08-11.json')
SENT = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-11.json')

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

news = json.load(open(NEWS))
sent = json.load(open(SENT))
# 盘中(015-024)与盘后(025-033)需要重标
target_ids = {f'N20260811-{i:03d}' for i in range(15, 34)}
target = [x for x in news if x['id'] in target_ids]
print(f'待标注 {len(target)} 条')

prompt = """你是财经新闻情绪分析器。对以下新闻逐条输出 JSON 数组，每条含字段：
id, sentiment(正面/中性/负面), strength(0-100整数), impact_direction(利多/利空/中性), expected_volatility(低/中/高), reason(30字内中文理由)
输出格式：只输出 JSON 数组，不要其他文字。

新闻列表：
"""
for x in target:
    prompt += f"\n[{x['id']}] 赛道={x['track']} 分类={x['category']}\n标题：{x['title']}\n摘要：{x['summary'][:200]}\n"

def call_ds(p):
    data = {
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": p}],
        "max_tokens": 8000,
        "temperature": 0.3,
    }
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
        print(f'  attempt {attempt+1} 空 content，重试')
        time.sleep(3)
    except Exception as e:
        print(f'  attempt {attempt+1} fail: {str(e)[:120]}')
        time.sleep(3)

if not content:
    print('ERROR: DeepSeek 3 次重试均失败，保留占位')
    raise SystemExit(1)

# 解析 JSON
content = content.strip()
if content.startswith('```'):
    content = content.strip('`')
    if content.startswith('json'):
        content = content[4:]
start = content.find('[')
end = content.rfind(']')
arr = json.loads(content[start:end+1])
print(f'解析到 {len(arr)} 条标注')

# 合并回 sentiment（盘前 14 条保留，覆盖 015-033）
by_id = {x['id']: x for x in arr}
updated = 0
for s in sent:
    if s['id'] in by_id:
        a = by_id[s['id']]
        for k in ['sentiment', 'strength', 'impact_direction', 'expected_volatility', 'reason']:
            s[k] = a.get(k, s.get(k))
        updated += 1
json.dump(sent, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'sentiment 更新 {updated} 条，total {len(sent)}')

# 同步回写 news JSON（sentiment/strength 等）
sent_by_id = {x['id']: x for x in sent}
for n in news:
    if n['id'] in sent_by_id:
        s = sent_by_id[n['id']]
        n['sentiment'] = s['sentiment']; n['strength'] = s['strength']
        n['impact_direction'] = s['impact_direction']; n['expected_volatility'] = s['expected_volatility']
        n['reason'] = s['reason']
json.dump(news, open(NEWS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('news JSON 情绪字段已同步')

# 打印标注结果
for a in arr:
    print(f"  {a['id']} {a['sentiment']} {a['strength']} {a['impact_direction']} {a['reason'][:30]}")
