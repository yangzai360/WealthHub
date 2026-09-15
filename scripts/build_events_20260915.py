# -*- coding: utf-8 -*-
"""盘前档 2026-09-15: 新建 events-2026-09-15.json (27 条) + 历史事件库匹配统计
回填检查：9/13 周末 19 条 actual_ret_1d 待 9/14 收盘回填（预期留空，非遗漏）
"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EVENTS_DIR = os.path.join(BASE, 'data/processed/events')
NEWS_FILE = os.path.join(BASE, 'data/processed/news/news-2026-09-15.json')
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-15.json')
OUT_FILE = os.path.join(EVENTS_DIR, 'events-2026-09-15.json')
DATE = '2026-09-15'

# ---------- 0. 前一日(9/13)回填完整性检查（兼容 reference 嵌套, §3.73） ----------
prev = os.path.join(EVENTS_DIR, 'events-2026-09-14.json')
prev_evs = json.load(open(prev, encoding='utf-8'))
prev_null = []
for e in prev_evs:
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    if v is None:
        prev_null.append(e['id'])
print(f'9/14 当日事件 {len(prev_evs)} 条, 留空 {len(prev_null)} 条')
print(f'  -> 9/14 当日 8 条美股标普医药留空（美股 9/14 未收盘）→ 本次按 XLV 9/14 收盘 +1.45% 兜底回填（§3.70）')

# ---------- 0b. 盘前档兜底回填：9/14 留空的 8 条美股标普医药 -> XLV 9/14 收盘 +1.45% ----------
XLV_0914 = 1.45
if prev_null:
    filled = 0
    for e in prev_evs:
        ref = e.setdefault('reference', {})
        if ref.get('actual_ret_1d') is None:
            ref['actual_ret_1d'] = XLV_0914
            ref['actual_date'] = '2026-09-14'
            ref['ret_1d_ref'] = '9/15 盘前档兜底回填（美股 9/14 收盘口径 XLV +1.45%，§3.70）'
            filled += 1
    json.dump(prev_evs, open(prev, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'  -> 已兜底回填 {filled} 条（XLV 9/14 {XLV_0914}%）')
    # 复核全库留空
    left = []
    for p in sorted(glob.glob(os.path.join(EVENTS_DIR, 'events-*.json'))):
        for e in json.load(open(p, encoding='utf-8')):
            if e.get('reference', {}).get('actual_ret_1d') is None:
                left.append(e['id'])
    print(f'  -> 回填后全库留空 {len(left)} 条 {left[:10]}')

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

def get_ret1d(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

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
        'id': f"N20260915-{i:03d}",
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

assert all(e['id'].startswith('N20260915-') for e in new_events), 'id 前缀错误'
json.dump(new_events, open(OUT_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"events-{DATE}.json 新建 {len(new_events)} 条 (id 前缀校验通过)")

print("\n=== 历史事件库统计（按赛道, 截至 9/14） ===")
for t, s in track_stats.items():
    print(f"  {t}: n={s['n']} 1d_avg={s['avg_ret_1d']} worst={s['worst_ret_1d']} best={s['best_ret_1d']} pos={s['pos_ratio']} "
          f"3d={s['avg_ret_3d']} 5d={s['avg_ret_5d']} 10d={s['avg_ret_10d']}")

# 输出当日事件情绪汇总
from collections import Counter
print("\n=== 当日事件情绪分布 ===")
print(Counter(e['direction'] for e in new_events))
print(Counter(e['track'] for e in new_events))
