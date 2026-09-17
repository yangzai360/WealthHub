# -*- coding: utf-8 -*-
"""盘前档 2026-09-17: ①兜底回填 9/16 美股标普医药留空（XLV 9/16 收盘 +0.07%）
②新建 events-2026-09-17.json（34 条）+ 历史事件库匹配统计
"""
import json, os, glob
from collections import defaultdict, Counter

BASE = '/Users/jieyang/Documents/WealthHub'
EVENTS_DIR = os.path.join(BASE, 'data/processed/events')
NEWS_FILE = os.path.join(BASE, 'data/processed/news/news-2026-09-17.json')
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-17.json')
OUT_FILE = os.path.join(EVENTS_DIR, 'events-2026-09-17.json')
DATE = '2026-09-17'

# ---------- 0. 前一日(9/16)兜底回填：12 条美股标普医药 -> XLV 9/16 收盘 +0.07% ----------
prev = os.path.join(EVENTS_DIR, 'events-2026-09-16.json')
prev_evs = json.load(open(prev, encoding='utf-8'))


def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v


prev_null = [e['id'] for e in prev_evs if get_ret1d(e) is None]
print(f'9/16 当日事件 {len(prev_evs)} 条, 留空 {len(prev_null)} 条')

XLV_0916 = 0.07
if prev_null:
    filled = 0
    for e in prev_evs:
        ref = e.setdefault('reference', {})
        if ref.get('actual_ret_1d') is None:
            ref['actual_ret_1d'] = XLV_0916
            ref['actual_date'] = '2026-09-16'
            ref['ret_1d_ref'] = '9/17 盘前档兜底回填（美股 9/16 收盘口径 XLV +0.07%，§3.70）'
            filled += 1
    json.dump(prev_evs, open(prev, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'  -> 已兜底回填 {filled} 条（XLV 9/16 +{XLV_0916}%）')

left = []
for p in sorted(glob.glob(os.path.join(EVENTS_DIR, 'events-*.json'))):
    for e in json.load(open(p, encoding='utf-8')):
        if get_ret1d(e) is None:
            left.append((e['date'], e['track'], e['id']))
print(f'  -> 回填后全库留空 {len(left)} 条 {left[:8]}')

# ---------- 1. 读取今日 news + sentiment ----------
news = json.load(open(NEWS_FILE, encoding='utf-8'))
sents = json.load(open(SENT_FILE, encoding='utf-8'))
sent_by_title = {s['title'][:40]: s for s in sents['items']}
print(f'news {len(news)} 条, sentiment {len(sents["items"])} 条')

# ---------- 2. 历史事件库统计 (排除当日) ----------
all_events = []
for p in sorted(glob.glob(os.path.join(EVENTS_DIR, 'events-*.json'))):
    if DATE in p:
        continue
    all_events.extend(json.load(open(p, encoding='utf-8')))

stats = defaultdict(lambda: {'n': 0, 'rets': [], 'ret3': [], 'ret5': [], 'ret10': [], 'pos': 0})
for e in all_events:
    t = e.get('track', '?')
    s = stats[t]
    r1 = get_ret1d(e)
    if r1 is not None:
        s['n'] += 1
        s['rets'].append(float(r1))
        if float(r1) > 0:
            s['pos'] += 1
    for k, arr in [('ret_3d', s['ret3']), ('ret_5d', s['ret5']), ('ret_10d', s['ret10'])]:
        v = e.get('reference', {}).get(k)
        if v is not None:
            arr.append(float(v))

track_stats = {}
for t, s in stats.items():
    track_stats[t] = {
        'n': s['n'],
        'avg_ret_1d': round(sum(s['rets']) / len(s['rets']), 2) if s['rets'] else None,
        'worst_ret_1d': round(min(s['rets']), 2) if s['rets'] else None,
        'best_ret_1d': round(max(s['rets']), 2) if s['rets'] else None,
        'pos_ratio': round(s['pos'] / s['n'], 2) if s['n'] else None,
        'avg_ret_3d': round(sum(s['ret3']) / len(s['ret3']), 2) if s['ret3'] else None,
        'avg_ret_5d': round(sum(s['ret5']) / len(s['ret5']), 2) if s['ret5'] else None,
        'avg_ret_10d': round(sum(s['ret10']) / len(s['ret10']), 2) if s['ret10'] else None,
        'max_vol': round(max([abs(r) for r in s['rets']]) * 2, 2) if s['rets'] else None,
    }

# ---------- 3. 新建当日事件 ----------
new_events = []
for i, n in enumerate(news, 1):
    t = n['track']
    s = sent_by_title.get(n['title'][:40], {})
    st = track_stats.get(t, {})
    new_events.append({
        'id': f"N20260917-{i:03d}",
        'date': DATE,
        'track': t,
        'category': n.get('category', '行业事件类'),
        'title': n['title'],
        'summary': n.get('summary', ''),
        'source': n.get('source', 'WebSearch'),
        'source_url': n.get('source_url', ''),
        'sentiment': s.get('sentiment', '中性'),
        'score': s.get('strength', 50),
        'strength': s.get('strength', 50),
        'direction': s.get('direction', '中性'),
        'volatility': s.get('volatility', '中'),
        'reason': s.get('brief', ''),
        'window': s.get('window', 'preopen'),
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

assert all(e['id'].startswith('N20260917-') for e in new_events), 'id 前缀错误'
json.dump(new_events, open(OUT_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"events-{DATE}.json 新建 {len(new_events)} 条 (id 前缀校验通过)")

# 写库后立即回读校验（§3.88 固化）
chk = json.load(open(OUT_FILE, encoding='utf-8'))
assert len(chk) == len(new_events), '回读条数不一致'
print(f'  -> 回读校验通过: {len(chk)} 条')

print("\n=== 历史事件库统计（按赛道, 截至 9/16 收盘回填） ===")
for t, s in track_stats.items():
    print(f"  {t}: n={s['n']} 1d_avg={s['avg_ret_1d']} worst={s['worst_ret_1d']} best={s['best_ret_1d']} pos={s['pos_ratio']} "
          f"3d={s['avg_ret_3d']} 5d={s['avg_ret_5d']} 10d={s['avg_ret_10d']}")

print("\n=== 当日事件情绪分布 ===")
print(Counter(e['direction'] for e in new_events))
print(Counter(e['track'] for e in new_events))

tot = 0
for p in sorted(glob.glob(os.path.join(EVENTS_DIR, 'events-*.json'))):
    tot += len(json.load(open(p, encoding='utf-8')))
print(f'\n全库事件总数: {tot}')
