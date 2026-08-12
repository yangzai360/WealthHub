# -*- coding: utf-8 -*-
"""事件库处理（2026-08-12 盘后）：
1) 回填 8/11 遗留美股医药事件 actual_ret_1d（XLV 8/11 -0.26% / IYH -0.35%）
2) 把 8/12 盘后新增 8 条新闻转事件追加 events-2026-08-12.json（当日全量 26 条）
3) 回填 8/12 当日事件 actual_ret_1d（赛道当日实际走势，美股标普医药留空待 8/13 盘前）
4) 汇总各赛道 1 日样本统计
"""
import json, os
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')

# ---------- 1. 回填 8/11 美股医药遗留（XLV 8/11 收盘 -0.26%） ----------
ev11 = json.load(open(os.path.join(EV, 'events-2026-08-11.json')))
x11_ret = -0.26  # XLV 8/11 收盘 -0.26%（新浪补更）
cnt11 = 0
for x in ev11:
    r = x['reference']
    if x['track'] == '美股标普医药' and r.get('actual_ret_1d') is None:
        r['actual_ret_1d'] = x11_ret
        r['actual_date'] = '2026-08-11'
        cnt11 += 1
json.dump(ev11, open(os.path.join(EV, 'events-2026-08-11.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'events-2026-08-11.json 美股医药回填 {cnt11} 条（XLV -0.26%）')

# ---------- 2. 追加 8/12 盘后新增新闻到事件库 ----------
news = json.load(open(os.path.join(BASE, 'data/processed/news/news-2026-08-12.json')))
sents = json.load(open(os.path.join(BASE, 'data/processed/news/sentiment-2026-08-12.json')))
sent_map = {s['id']: s for s in sents}
ev12 = json.load(open(os.path.join(EV, 'events-2026-08-12.json')))
existing_ids = {x['id'] for x in ev12}
added = 0
for n in news:
    if n['id'] not in existing_ids:
        s = sent_map.get(n['id'], {})
        ev12.append({
            'id': n['id'], 'date': '2026-08-12', 'track': n['track'], 'category': n['category'],
            'title': n['title'], 'summary': n['summary'], 'source': n['source'],
            'source_url': n['source_url'], 'sentiment': s.get('sentiment', '中性'), 'strength': s.get('strength', 50),
            'impact_direction': s.get('impact_direction', '中性'), 'expected_volatility': s.get('expected_volatility', '中'),
            'reason': s.get('reason', ''),
            'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None, 'max_vol': None,
                          'confidence': None, 'actual_ret_1d': None, 'actual_date': None, 'ret_1d_ref': None}
        })
        existing_ids.add(n['id'])
        added += 1
print(f'events-2026-08-12.json +{added} 条，total {len(ev12)}')

# ---------- 3. 回填 8/12 当日事件 actual_ret_1d ----------
track_ret = {
    'A股医药': -0.29,      # 医药ETF广发 159938 收盘 -0.29%
    '大消费': 0.25,         # 中证消费 12823.67 +0.25%
    '恒生科技': -0.99,      # HSTECH -0.99%
    '宏观': 0.32,           # 上证指数 +0.32%
    '其他/宽基': 0.32,      # 上证指数近似
}
cnt12 = 0
for x in ev12:
    r = x['reference']
    if r.get('actual_ret_1d') is not None:
        continue
    if x['track'] in track_ret:
        r['actual_ret_1d'] = track_ret[x['track']]
        r['actual_date'] = '2026-08-12'
        cnt12 += 1
    # 美股标普医药留空（8/12 美股未开盘，待 8/13 盘前用 XLV/IYH 回填）
json.dump(ev12, open(os.path.join(EV, 'events-2026-08-12.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'8/12 当日回填 {cnt12} 条；美股标普医药留空 {sum(1 for x in ev12 if x["track"]=="美股标普医药" and x["reference"].get("actual_ret_1d") is None)} 条待 8/13')

# ---------- 4. 汇总统计 ----------
all_ev = []
for f in sorted(os.listdir(EV)):
    if f.startswith('events-') and f.endswith('.json'):
        all_ev += json.load(open(os.path.join(EV, f)))
print('事件库全量累计:', len(all_ev), '条')
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
print('\n赛道 1 日样本统计（含 8/12）:')
for t, s in stats.items():
    def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None
    print(f"  {t}: n={s['n']} 均值={avg(s['rets'])} | 强正面 n={s['strong_pos']['n']} 均值={avg(s['strong_pos']['rets'])} | 强负面 n={s['strong_neg']['n']} 均值={avg(s['strong_neg']['rets'])}")
