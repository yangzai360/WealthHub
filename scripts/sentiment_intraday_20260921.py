# -*- coding: utf-8 -*-
"""2026-09-21 盘中档情绪标注（DeepSeek v4-flash, max_tokens=8000）
仅标注本档新增的 24 条（news 文件索引 35..58），合并进 sentiment-2026-09-21.json（保留盘前 35 条）
⚠️ §3.88 固化: 必须为每条 item 写 per-item `window` 字段（文件级字段不可替代）
"""
import json, urllib.request, os

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news')
DATE = '2026-09-21'
WINDOW = 'intraday'
PRE_N = 35          # 盘前条数

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    key = json.load(f)['deepseek']['key']

all_items = json.load(open(os.path.join(NEWS, f'news-{DATE}.json'), encoding='utf-8'))
items = all_items[PRE_N:]
print(f'载入 {len(all_items)} 条，本档标注 {len(items)} 条')

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

BATCH = 5
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
    print(f'  批{bi//BATCH+1} 完成 {len(arr)} 条 | strength={[o["strength"] for o in arr]}')

# ---- 合并（保留盘前 35 条）----
# ⚠️ 结构为 {date, window, count, items:[...]}，非裸 list（本档踩坑 1 次）
S = os.path.join(NEWS, f'sentiment-{DATE}.json')
if os.path.exists(S):
    doc = json.load(open(S, encoding='utf-8'))
    if isinstance(doc, dict):
        old = doc.get('items', [])
        old_window = doc.get('window', '')
    else:
        old, old_window = doc, ''
else:
    old, old_window = [], ''
print(f'已有 sentiment {len(old)} 条 (window={old_window})')
new_block = []
for i, it in enumerate(items, 1):
    o = results.get(i)
    if not o:
        print('  ⚠️ 缺标注 idx', i); continue
    new_block.append({**it,
                      "sentiment": o['sentiment'], "strength": int(o['strength']),
                      "confidence": int(o['confidence']), "direction": o['direction'],
                      "volatility": o['volatility'], "brief": o['brief'],
                      "window": WINDOW, "date": DATE})
merged = old + new_block
out = {"date": DATE,
       "window": old_window + " + 盘中(07:30-13:30)" if old_window else "盘中(07:30-13:30)",
       "count": len(merged), "items": merged}
json.dump(out, open(S, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

from collections import Counter
c = Counter(x['sentiment'] for x in new_block)
d = Counter(x['direction'] for x in new_block)
print(f'\n写入 {len(merged)} 条（本档 {len(new_block)}）')
print('情绪:', dict(c), '方向:', dict(d))
print('均值强度:', round(sum(x['strength'] for x in new_block)/len(new_block), 1))
miss = [i for i, it in enumerate(items, 1) if i not in results]
print('缺失标注:', miss if miss else '无')
