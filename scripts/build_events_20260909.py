# -*- coding: utf-8 -*-
"""盘前档 2026-09-09: 新建 events-2026-09-09.json (15 条) + 历史事件库匹配统计
9/8 30 条已全量回填(N20260908-013 用 XLV 9/8 -2.52% 完成), 全库 0 留空; 9/9 新增 15 条 actual_ret_1d 待今日收盘回填"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EVENTS_DIR = os.path.join(BASE, 'data/processed/events')
NEWS_FILE = os.path.join(BASE, 'data/processed/news/news-2026-09-09.json')
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-09.json')
OUT_FILE = os.path.join(EVENTS_DIR, 'events-2026-09-09.json')

with open(NEWS_FILE, encoding='utf-8') as f:
    news = json.load(f)
with open(SENT_FILE, encoding='utf-8') as f:
    sents = json.load(f)
# 合并情绪到 news
sent_by_title = {s['title'][:40]: s for s in sents}
for n in news:
    s = sent_by_title.get(n['title'][:40], {})
    n['sentiment'] = s.get('sentiment', '中性')
    n['score'] = s.get('score', 50)
    n['strength'] = s.get('strength', s.get('score', 50))
    n['direction'] = s.get('direction', '中性')
    n['volatility'] = s.get('volatility', '中')
    n['reason'] = s.get('comment', '')

# ---------- 历史事件库统计 (截至 9/8, 排除当日) ----------
all_events = []
for p in sorted(glob.glob(os.path.join(EVENTS_DIR, 'events-*.json'))):
    if '2026-09-09' in p:
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

stats = defaultdict(lambda: {'n': 0, 'rets': [], 'ret3': [], 'ret5': [], 'ret10': [], 'pos': 0})
for e in all_events:
    t = e.get('track', '?')
    s = stats[t]
    r1 = get_ret1d(e)
    if r1 is not None:
        s['n'] += 1
        s['rets'].append(float(r1))
        if float(r1) > 0: s['pos'] += 1
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

# ---------- 新建当日事件 (15 条) ----------
new_events = []
for i, n in enumerate(news, 1):
    t = n['track']
    st = track_stats.get(t, {})
    new_events.append({
        'id': f"N20260909-{i:03d}",
        'date': '2026-09-09',
        'track': t,
        'category': n.get('category', '行业事件类'),
        'title': n['title'],
        'summary': n.get('summary', ''),
        'source': 'WebSearch',
        'source_url': n.get('source_url', ''),
        'sentiment': n.get('sentiment', '中性'),
        'score': n.get('score', 50),
        'strength': n.get('strength', n.get('score', 50)),
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
    json.dump(new_events, f, ensure_ascii=False, indent=1)
print(f"events-2026-09-09.json 新建 {len(new_events)} 条")
for e in new_events:
    print(f"  {e['id']} [{e['track']}] {e['sentiment']}{e['score']}/{e['strength']} | {e['title'][:38]}")

print("\n=== 历史事件 1日收益统计（按赛道, 截至 9/8 收盘回填） ===")
for t, s in track_stats.items():
    print(f"  {t}: n={s['n']} avg={s['avg_ret_1d']} worst={s['worst_ret_1d']} best={s['best_ret_1d']} pos={s['pos_ratio']} 3d={s['avg_ret_3d']} 5d={s['avg_ret_5d']} 10d={s['avg_ret_10d']}")

# 全局留空统计
total = 0
nulls = 0
for p in sorted(glob.glob(os.path.join(EVENTS_DIR, 'events-*.json'))):
    with open(p, encoding='utf-8') as f:
        evs = json.load(f)
    for e in evs:
        total += 1
        r1 = e.get('actual_ret_1d')
        if r1 is None:
            r1 = e.get('reference', {}).get('actual_ret_1d')
        if r1 is None:
            nulls += 1
            print(f"  NULL: {e.get('id')} in {os.path.basename(p)}")
print(f"\n全库事件 {total} 条, 留空 {nulls} 条(9/9 当日 15 条待收盘回填属正常)")
