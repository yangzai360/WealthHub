# -*- coding: utf-8 -*-
"""2026-08-17 盘前：事件库写入（12条）+ 历史匹配统计（按track的1日收益/3-5-10日参考）"""
import json, os, glob

BASE = '/Users/jieyang/Documents/WealthHub'
EVENTS_DIR = os.path.join(BASE, 'data/processed/events')
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-17.json')
OUT_FILE = os.path.join(EVENTS_DIR, 'events-2026-08-17.json')

with open(SENT_FILE, encoding='utf-8') as f:
    news = json.load(f)

# ---------- 1. 读取历史事件库 ----------
all_events = []
for p in sorted(glob.glob(os.path.join(EVENTS_DIR, 'events-*.json'))):
    if '2026-08-17' in p:
        continue
    with open(p, encoding='utf-8') as f:
        all_events.extend(json.load(f))

def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

def get_ret(e, k):
    return e.get('reference', {}).get(k)

# ---------- 2. 历史匹配统计 ----------
from collections import defaultdict
stats = defaultdict(lambda: {'n': 0, 'rets': [], 'ret3': [], 'ret5': [], 'ret10': [], 'pos': 0, 'neg': 0})
for e in all_events:
    t = e.get('track', '?')
    s = stats[t]
    r1 = get_ret1d(e)
    if r1 is not None:
        s['n'] += 1
        s['rets'].append(float(r1))
        if float(r1) > 0: s['pos'] += 1
        else: s['neg'] += 1
    for k, arr in [('ret_3d', s['ret3']), ('ret_5d', s['ret5']), ('ret_10d', s['ret10'])]:
        v = get_ret(e, k)
        if v is not None:
            arr.append(float(v))

track_stats = {}
for t, s in stats.items():
    track_stats[t] = {
        'n': s['n'],
        'avg_ret_1d': round(sum(s['rets'])/len(s['rets']), 2) if s['rets'] else None,
        'worst_ret_1d': round(min(s['rets']), 2) if s['rets'] else None,
        'best_ret_1d': round(max(s['rets']), 2) if s['rets'] else None,
        'pos_ratio': round(s['pos']/s['n'], 2) if s['n'] else None,
        'avg_ret_3d': round(sum(s['ret3'])/len(s['ret3']), 2) if s['ret3'] else None,
        'avg_ret_5d': round(sum(s['ret5'])/len(s['ret5']), 2) if s['ret5'] else None,
        'avg_ret_10d': round(sum(s['ret10'])/len(s['ret10']), 2) if s['ret10'] else None,
        'max_vol': round(max([abs(r) for r in s['rets']])*2, 2) if s['rets'] else None,
    }
print('=== 历史事件 1日收益统计（按赛道） ===')
for t, s in track_stats.items():
    print(f"  {t}: n={s['n']} avg={s['avg_ret_1d']} worst={s['worst_ret_1d']} best={s['best_ret_1d']} pos={s['pos_ratio']} ret3d={s['avg_ret_3d']} ret5d={s['avg_ret_5d']} ret10d={s['avg_ret_10d']}")

# ---------- 3. 生成今日事件 ----------
events = []
for i, n in enumerate(news, 1):
    t = n.get('track', '其他/宽基')
    st = track_stats.get(t, {})
    events.append({
        'id': f'N20260817-{i:03d}',
        'date': '2026-08-17',
        'track': t,
        'category': n.get('category', '行业事件类'),
        'title': n['title'],
        'summary': n.get('summary', ''),
        'source': n.get('source', 'WebSearch'),
        'source_url': n.get('source_url', ''),
        'sentiment': n.get('sentiment', '中性'),
        'score': n.get('score', 50),
        'strength': n.get('strength', 50),
        'direction': n.get('direction', '中性'),
        'volatility': n.get('volatility', '中'),
        'reason': n.get('reason', ''),
        'reference': {
            'ret_3d': st.get('avg_ret_3d'),
            'ret_5d': st.get('avg_ret_5d'),
            'ret_10d': st.get('avg_ret_10d'),
            'max_vol': st.get('max_vol'),
            'confidence': min(90, 40 + st.get('n', 0) * 2),
            'actual_ret_1d': None,
            'actual_date': None,
            'ret_1d_ref': {
                'track_n': st.get('n'),
                'track_avg': st.get('avg_ret_1d'),
                'track_worst': st.get('worst_ret_1d'),
                'track_best': st.get('best_ret_1d'),
                'track_pos_ratio': st.get('pos_ratio'),
            }
        }
    })

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(events, f, ensure_ascii=False, indent=1)
print(f'\nDONE -> events-2026-08-17.json ({len(events)} 条)')
