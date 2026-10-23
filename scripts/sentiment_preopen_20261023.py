# -*- coding: utf-8 -*-
"""2026-10-23 盘前档情绪标注（规则表模式）：
- 输入 news-2026-10-23.json（30 条，window 已逐条写入，§3.103）
- 输出 sentiment-2026-10-23.json（items 含 window/session_type，供 events / history_ref 按 window 过滤）
- §3.127b：DeepSeek v4-flash HTTP 402（连续第 17 个日历日）→ 全部走规则表，annotation_mode = rule_table，
  逐条写 degraded=true / degrade_reason，`degraded_items` 计数落库，禁止静默降级。
"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
TODAY = '2026-10-23'
NEWS = os.path.join(BASE, f'data/processed/news/news-{TODAY}.json')
OUT = os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json')

news = json.load(open(NEWS, encoding='utf-8'))
if not news:
    raise SystemExit('news 为空，终止')

items = []
for i, x in enumerate(news, 1):
    items.append({
        'idx': i, 'title': x['title'], 'track': x['track'], 'window': x['window'],
        'sentiment': x['sentiment'], 'strength': x['strength'], 'confidence': x['confidence'],
        'direction': x['direction'], 'volatility': x['volatility'], 'brief': x['brief'],
        'source_url': x.get('source_url', ''), 'category': x['category'],
        'degraded': True,
        'degrade_reason': 'DeepSeek v4-flash 端点 HTTP 402（Payment Required）→ 按 §3.127b 降级为规则表标注，未做模型二次复核',
    })

by_track = defaultdict(lambda: {'n': 0, 'sum': 0.0, 'pos': 0, 'neu': 0, 'neg': 0, 'strength_sum': 0})
for x in items:
    t = by_track[x['track']]
    t['n'] += 1
    sg = 1 if x['direction'] == '利多' else (-1 if x['direction'] == '利空' else 0)
    t['sum'] += sg * x['strength'] / 100
    t['strength_sum'] += x['strength']
    t['pos' if x['sentiment'] == '正面' else ('neg' if x['sentiment'] == '负面' else 'neu')] += 1

out = {
    'date': TODAY,
    'window': news[0]['window'],
    'count': len(items),
    'session_type': 'normal_trading_day_preopen',
    'session_type_note': '档型③「正常交易日盘前」= A股 10/23 正常交易日 + 港股 10/23 正常交易日（10/22 已复市并收盘）+ 美股 10/23 正常交易日（08:00 A股/港股 均无当日价格）',
    'annotation_mode': 'rule_table',
    'degraded_items': len(items),
    'degraded_batches': 1,
    'degradation_reason': 'DeepSeek v4-flash HTTP 402（连续第 17 个日历日）；402 ≠ 429 → 停止重试并降级（§3.127b）',
    'by_track': {k: {**{kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()}} for k, v in by_track.items()},
    'mean_strength': round(sum(x['strength'] for x in items) / len(items), 2),
    'net_nominal': round(sum(by_track[k]['sum'] for k in by_track), 4),
    'items': items,
}
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('written', OUT, 'n=', len(items))
print('mean_strength', out['mean_strength'], 'net_nominal', out['net_nominal'])
for k, v in out['by_track'].items():
    print(f"  {k:8s} n={v['n']} 正{v['pos']}/中{v['neu']}/负{v['neg']} 净分={v['sum']:+.4f} 均强度={v['strength_sum']/v['n']:.2f}")
