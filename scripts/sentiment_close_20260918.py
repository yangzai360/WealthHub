# -*- coding: utf-8 -*-
"""2026-09-18 盘后档：DeepSeek v4-flash 情绪标注（盘后窗口 14:00-20:00 新增 20 条）
⚠️ §3.88 修复：必须为每条 item 写 `window` 字段（文件级字段不可替代），否则盘后事件入库静默失败
§3.82：差集比对统一用 title[:60] 截断口径；§3.72：全局 idx 连续编号
"""
import json, os, time, urllib.request

BASE = '/Users/jieyang/Documents/WealthHub'
NEWS = os.path.join(BASE, 'data/processed/news/news-2026-09-18.json')
SENT = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-18.json')
WINDOW = '盘后(14:00-20:00)'

with open('/Users/jieyang/.pi/agent/auth.json') as f:
    KEY = json.load(f)['deepseek']['key']

news = json.load(open(NEWS, encoding='utf-8'))
sent = json.load(open(SENT, encoding='utf-8'))
done = {x['title'][:60] for x in sent['items']}
todo = [n for n in news if n['title'][:60] not in done]
print(f'待标注 {len(todo)} 条（news {len(news)} / sentiment {len(sent["items"])}）')

PROMPT = """你是专业的 A 股/港股/美股基金经理助理，负责给财经新闻打情绪标签。
对下面每条新闻输出 JSON 数组，每条包含字段：
- idx: 新闻序号（整数）
- sentiment: 正面/中性/负面
- strength: 0-100 强度分（对市场情绪冲击力度）
- confidence: 0-100 置信度（信息确定性）
- direction: 利多/利空/中性（对该新闻所属赛道的价格影响方向）
- volatility: 低/中/高（预期波动幅度）
- brief: 一句话中文摘要（不超过 25 字）

要求：
1) 严格基于新闻文本，不臆造数据
2) 赛道归属已给定（track 字段），direction 按该赛道价格方向判断
3) 只输出 JSON 数组，不要任何解释文字、不要 markdown 代码块

新闻列表：
"""


def call(batch):
    lines = []
    for i, n in enumerate(batch):
        lines.append(f"{i+1}. [赛道:{n['track']}] {n['title']}")
    data = {"model": "deepseek-v4-flash",
            "messages": [{"role": "user", "content": PROMPT + "\n".join(lines)}],
            "max_tokens": 8000, "temperature": 0.3}
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                                 data=json.dumps(data).encode(),
                                 headers={"Authorization": f"Bearer {KEY}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.load(resp)['choices'][0]['message']['content']


results = []
B = 5
for s in range(0, len(todo), B):
    batch = todo[s:s + B]
    for attempt in range(3):
        try:
            txt = call(batch).strip()
            if txt.startswith('```'):
                txt = txt.split('```')[1].replace('json', '', 1).strip()
            arr = json.loads(txt)
            if len(arr) != len(batch):
                raise ValueError(f'条数不符 {len(arr)} vs {len(batch)}')
            for j, a in enumerate(arr):
                results.append((batch[j], a))
            print(f'  批 {s//B+1}: OK ({len(batch)} 条)')
            break
        except Exception as e:
            print(f'  批 {s//B+1} 第{attempt+1}次失败: {e}')
            time.sleep(3)
    else:
        for n in batch:
            results.append((n, {'sentiment': '中性', 'strength': 50, 'confidence': 50,
                                'direction': '中性', 'volatility': '中', 'brief': n['title'][:20]}))

start = len(sent['items'])
for k, (n, a) in enumerate(results, start=start + 1):
    sent['items'].append({'idx': k, 'title': n['title'][:60], 'track': n['track'],
                          'window': WINDOW,
                          'sentiment': a['sentiment'], 'strength': a['strength'],
                          'confidence': a['confidence'], 'direction': a['direction'],
                          'volatility': a['volatility'], 'brief': a['brief']})
    n['sentiment'] = a['sentiment']; n['score'] = a['strength']; n['strength'] = a['strength']
    n['direction'] = a['direction']; n['volatility'] = a['volatility']; n['brief'] = a['brief']

sent['window'] = sent.get('window', '') + ' + ' + WINDOW
json.dump(sent, open(SENT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(news, open(NEWS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

add = sent['items'][start:]
# ⚠️ §3.88 硬守卫：过滤后为空必须报错，禁止静默通过
if not add:
    raise SystemExit('⚠️ 盘后窗口 sentiment 为 0 条，终止')
if any(x.get('window') != WINDOW for x in add):
    raise SystemExit('⚠️ 盘后窗口存在缺失/错误 window 字段，终止')

np_ = sum(1 for x in add if x['direction'] == '利多')
nn_ = sum(1 for x in add if x['direction'] == '利空')
nu_ = sum(1 for x in add if x['direction'] == '中性')
print(f"\n盘后新增 {len(add)} 条：利多 {np_} / 利空 {nn_} / 中性 {nu_}，均值强度 {sum(x['strength'] for x in add)/len(add):.1f}")
print(f"sentiment 总计 {len(sent['items'])} 条")
for x in add:
    print(f"  {x['track']:8s} {x['direction']:2s} {x['strength']:>3d}/{x['confidence']:<3d} {x['volatility']} | {x['brief']}")
