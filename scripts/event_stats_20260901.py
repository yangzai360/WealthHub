# -*- coding: utf-8 -*-
"""盘前档 2026-09-01：生成 event_stats_20260901.json（与 append_events 统计口径一致）"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
TODAY = '2026-09-01'

def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

all_ev = []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    all_ev += json.load(open(f, encoding='utf-8'))

nulls = [x for x in all_ev if get_ret1d(x) is None]
final = defaultdict(lambda: {'n': 0, 'rets': [], 'sp': {'n': 0, 'rets': []}, 'sn': {'n': 0, 'rets': []}, 'dir_ok': 0, 'dir_n': 0})
for x in all_ev:
    v = get_ret1d(x)
    if v is None:
        continue
    t = x.get('track', '?'); s = final[t]
    s['n'] += 1; s['rets'].append(float(v))
    strength = x.get('strength') or x.get('score') or 0
    if strength >= 60 and x.get('sentiment') == '正面':
        s['sp']['n'] += 1; s['sp']['rets'].append(float(v))
    if strength >= 60 and x.get('sentiment') == '负面':
        s['sn']['n'] += 1; s['sn']['rets'].append(float(v))
    senti = x.get('sentiment')
    if senti in ('正面', '负面'):
        s['dir_n'] += 1
        if (senti == '正面' and float(v) > 0) or (senti == '负面' and float(v) < 0):
            s['dir_ok'] += 1

def avg(lst): return round(sum(lst)/len(lst), 2) if lst else None

tracks_out = {}
tot_n = tot_ok = tot_sample = 0
for t, s in sorted(final.items()):
    tracks_out[t] = {
        'n': s['n'], 'avg': avg(s['rets']), 'worst': round(min(s['rets']), 2) if s['rets'] else None,
        'best': round(max(s['rets']), 2) if s['rets'] else None,
        'strong_pos_n': s['sp']['n'], 'strong_pos_avg': avg(s['sp']['rets']),
        'strong_neg_n': s['sn']['n'], 'strong_neg_avg': avg(s['sn']['rets']),
        'dir_ok': s['dir_ok'], 'dir_n': s['dir_n'],
    }
    tot_n += s['dir_n']; tot_ok += s['dir_ok']; tot_sample += s['n']

out = {
    'date': TODAY,
    'total_events': len(all_ev),
    'null_actual_ret_1d': len(nulls),
    'null_ids': [x.get('id') for x in nulls],
    'one_day_samples': tot_sample,
    'direction_ok': tot_ok,
    'direction_n': tot_n,
    'direction_ratio': round(tot_ok/tot_n, 2) if tot_n else None,
    'tracks': tracks_out,
}
with open(os.path.join(BASE, 'data/processed/history/event_stats_20260901.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f'event_stats_20260901.json 已生成：total={len(all_ev)} null={len(nulls)} 样本={tot_sample} 方向={tot_ok}/{tot_n}')
