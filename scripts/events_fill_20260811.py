# -*- coding: utf-8 -*-
"""事件库处理：
1) 回填 8/10 遗留 3 条美股医药事件 actual_ret_1d（XLV 8/10 +1.67%）
2) 把 8/11 盘后新增 9 条新闻转事件追加 events-2026-08-11.json
3) 回填 8/11 当日事件 actual_ret_1d（赛道当日实际走势，美股医药留空待 8/12 盘前）
"""
import json, os, re, datetime

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
NEWS = os.path.join(BASE, 'data/processed/news/news-2026-08-11.json')

# ---------- 1. 回填 8/10 美股医药遗留 ----------
ev10 = json.load(open(os.path.join(EV, 'events-2026-08-10.json')))
x10_ret = 1.67  # XLV 8/10 收盘 +1.67%
cnt10 = 0
for x in ev10:
    r = x['reference']
    if x['track'] == '美股标普医药' and r.get('actual_ret_1d') is None:
        r['actual_ret_1d'] = x10_ret
        r['actual_date'] = '2026-08-10'
        cnt10 += 1
json.dump(ev10, open(os.path.join(EV, 'events-2026-08-10.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'events-2026-08-10.json 回填 {cnt10} 条（XLV +1.67%）')

# ---------- 2. 追加 8/11 盘后事件 ----------
news = json.load(open(NEWS))
ev11 = json.load(open(os.path.join(EV, 'events-2026-08-11.json')))
existing_ids = {x['id'] for x in ev11}
# 新闻中已是事件的 id 前缀 N，事件库保持相同 id 体系
added = 0
for n in news:
    if n['id'] not in existing_ids:
        ev11.append({
            'id': n['id'], 'date': n['date'], 'track': n['track'], 'category': n['category'],
            'title': n['title'], 'summary': n['summary'], 'source': n['source'],
            'source_url': n['source_url'], 'sentiment': n['sentiment'], 'strength': n['strength'],
            'impact_direction': n['impact_direction'], 'expected_volatility': n['expected_volatility'],
            'reason': n['reason'],
            'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None, 'max_vol': None,
                          'confidence': None, 'actual_ret_1d': None, 'actual_date': None, 'ret_1d_ref': None}
        })
        existing_ids.add(n['id'])
        added += 1
print(f'events-2026-08-11.json +{added} 条，total {len(ev11)}')

# ---------- 3. 回填 8/11 当日事件 actual_ret_1d ----------
track_ret = {
    'A股医药': -0.15,      # 医药ETF广发 159938 收盘 -0.15%（冲高回落）
    '大消费': -1.14,        # 中证消费 -1.14%
    '恒生科技': -1.93,      # HSTECH -1.93%
    '宏观': -0.82,          # 上证指数 -0.82%
}
cnt11 = 0
for x in ev11:
    r = x['reference']
    if r.get('actual_ret_1d') is not None:
        continue
    if x['track'] in track_ret:
        r['actual_ret_1d'] = track_ret[x['track']]
        r['actual_date'] = '2026-08-11'
        cnt11 += 1
    # 美股标普医药留空（8/11 未开盘，待 8/12 盘前用 XLV/IYH 回填）
json.dump(ev11, open(os.path.join(EV, 'events-2026-08-11.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'8/11 当日回填 {cnt11} 条；美股标普医药留空 {sum(1 for x in ev11 if x["track"]=="美股标普医药" and x["reference"].get("actual_ret_1d") is None)} 条待 8/12')

# ---------- 4. 汇总统计 ----------
all_ev = []
for f in sorted(os.listdir(EV)):
    if f.startswith('events-') and f.endswith('.json'):
        all_ev += json.load(open(os.path.join(EV, f)))
print('事件库全量累计:', len(all_ev), '条')
# 各赛道 1 日样本统计（含 8/11 当日）
from collections import defaultdict
stats = defaultdict(lambda: {'n': 0, 'rets': [], 'strong_pos': {'n': 0, 'rets': []}, 'strong_neg': {'n': 0, 'rets': []}})
for x in all_ev:
    r = x['reference']
    if r.get('actual_ret_1d') is None:
        continue
    t = x['track']; s = stats[t]
    s['n'] += 1; s['rets'].append(r['actual_ret_1d'])
    if x['strength'] >= 60 and x['sentiment'] == '正面':
        s['strong_pos']['n'] += 1; s['strong_pos']['rets'].append(r['actual_ret_1d'])
    if x['strength'] >= 60 and x['sentiment'] == '负面':
        s['strong_neg']['n'] += 1; s['strong_neg']['rets'].append(r['actual_ret_1d'])
print('\n赛道 1 日样本统计（含 8/11）:')
for t, s in stats.items():
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['strong_pos']['n']} 均值={avg(s['strong_pos']['rets'])} | 强负面 n={s['strong_neg']['n']} 均值={avg(s['strong_neg']['rets'])}")
