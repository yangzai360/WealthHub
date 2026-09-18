# -*- coding: utf-8 -*-
"""2026-09-18 盘前档情绪标注（DeepSeek v4-flash, max_tokens=8000）
分批标注（每批 7 条），results key 用全局偏移（§3.72 教训）
⚠️ §3.88 固化: 必须为每条 item 写 per-item `window` 字段（文件级字段不可替代）
"""
import json, urllib.request, os

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news')
DATE = '2026-09-18'
WINDOW = 'preopen'

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
        o = {"sentiment": "中性", "strength": 50, "confidence": 50,
             "direction": "中性", "volatility": "中", "brief": "标注缺失"}
    rec = dict(items[gi])
    rec['window'] = WINDOW          # ⚠️ §3.88: per-item window 必写
    rec['sentiment'] = o['sentiment']
    rec['strength'] = int(o['strength'])
    rec['confidence'] = int(o['confidence'])
    rec['direction'] = o['direction']
    rec['volatility'] = o['volatility']
    rec['brief'] = o.get('brief', '')
    out.append(rec)

dst = os.path.join(NEWS, f'sentiment-{DATE}.json')
json.dump({"date": DATE, "window": WINDOW, "count": len(out), "items": out},
          open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 硬守卫: 过滤后必须非空（§3.88）
chk = [x for x in out if x.get('window') == WINDOW]
if not chk:
    raise SystemExit('preopen window 过滤结果为空，疑似 window 字段缺失')
print(f'已写入 {dst}: {len(out)} 条（window={WINDOW} 过滤后 {len(chk)} 条）')

from collections import Counter
print('情绪:', Counter(x['sentiment'] for x in out))
print('方向:', Counter(x['direction'] for x in out))
print('均值强度:', round(sum(x['strength'] for x in out) / len(out), 1))
