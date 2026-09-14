# -*- coding: utf-8 -*-
"""2026-09-14 盘后: DeepSeek 情绪标注盘后新增 11 条（幂等，只标注 news 中无 sentiment 的条目）
结果追加到 sentiment-2026-09-14.json，并回写 news-2026-09-14.json"""
import json, os, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news')
DATE = '2026-09-14'
NEWS_FILE = os.path.join(NEWS, f'news-{DATE}.json')
SENT_FILE = os.path.join(NEWS, f'sentiment-{DATE}.json')

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

news = json.load(open(NEWS_FILE, encoding='utf-8'))
sent = json.load(open(SENT_FILE, encoding='utf-8'))
sent_titles = set(x['title'] for x in sent['items'])

pending = [n for n in news if n['title'] not in sent_titles]
print(f'待标注 {len(pending)} 条 / 已有 {len(sent["items"])} 条')

prompt_head = """你是资深证券分析师。请对下列每条财经新闻做情绪标注，严格只输出 JSON 数组，不要任何解释文字。
每条输出字段：
- idx: 序号(从1开始，沿用输入给出的编号)
- sentiment: "正面"|"中性"|"负面"
- strength: 0-100 整数(情绪强度)
- confidence: 0-100 整数(对A股/港股/美股相关赛道影响的置信度)
- direction: "利多"|"利空"|"中性"
- volatility: "高"|"中"|"低"(预期波动幅度)
- brief: 一句话影响判断(不超过40字)

新闻列表：
"""

BATCH = 6
results = {}
for bi in range(0, len(pending), BATCH):
    chunk = pending[bi:bi + BATCH]
    prompt = prompt_head
    for j, it in enumerate(chunk, 1):
        prompt += f"{j}. [track={it['track']}] {it['title'][:200]}\n"
    data = {"model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8192, "temperature": 0.3}
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
    arr = json.loads(content[s:e + 1])
    for o in arr:
        results[bi + int(o['idx'])] = o
    print(f'  批{bi//BATCH+1} 完成 {len(arr)} 条')

base_idx = len(sent['items'])
for gi, it in enumerate(pending):
    o = results.get(gi + 1)
    if o is None:
        print(f'  WARN 第 {gi+1} 条未标注:', it['title'][:40]); continue
    sent['items'].append({
        'idx': base_idx + gi + 1, 'title': it['title'][:60], 'track': it['track'],
        'sentiment': o['sentiment'], 'strength': int(o['strength']),
        'confidence': int(o['confidence']), 'direction': o['direction'],
        'volatility': o['volatility'], 'brief': o.get('brief', ''),
        'source_url': it.get('source_url', ''), 'window': '盘后(13:30-20:00)',
    })
    it['sentiment'] = o['sentiment']; it['score'] = int(o['strength'])
    it['strength'] = int(o['strength']); it['direction'] = o['direction']
    it['volatility'] = o['volatility']; it['brief'] = o.get('brief', '')

sent['window'] = sent['window'] + ' | 盘后(13:30-20:00) 追加 %d 条' % len(pending)
json.dump(sent, open(SENT_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(news, open(NEWS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

new_items = sent['items'][base_idx:]
for o in new_items:
    print(f"  {o['idx']:2d} {o['track']:8s} {o['sentiment']} {o['strength']:3d}/{o['confidence']:3d} {o['direction']} {o['volatility']} | {o['brief']}")
print(f"\n盘后新增 {len(new_items)} 条: 利多 {sum(1 for o in new_items if o['direction']=='利多')} / "
      f"利空 {sum(1 for o in new_items if o['direction']=='利空')} / 中性 {sum(1 for o in new_items if o['direction']=='中性')}")
print(f"当日累计 {len(sent['items'])} 条")
