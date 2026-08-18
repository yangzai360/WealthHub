# -*- coding: utf-8 -*-
"""2026-08-18 盘中: 事件库追加 11 条盘中新闻 (id 019-029) + 历史匹配统计"""
import json, os, glob

BASE = '/Users/jieyang/Documents/WealthHub'
EVENTS_DIR = os.path.join(BASE, 'data/processed/events')
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-08-18.json')
OUT_FILE = os.path.join(EVENTS_DIR, 'events-2026-08-18.json')

with open(SENT_FILE, encoding='utf-8') as f:
    news = json.load(f)
with open(OUT_FILE, encoding='utf-8') as f:
    existing = json.load(f)

existing_titles = set(e['title'][:40] for e in existing)

# 盘中 11 条手动归类赛道（track 用赛道名，禁止 category 名）
TRACK_MAP = {
    "港股午评：恒生科技大跌1.99%": "恒生科技",
    "港股科网全线下挫三大利空": "恒生科技",
    "A股午评：沪指冲4000点未果回落": "宏观",
    "商务部等9部门联合印发": "大消费",
    "大消费板块盘中持续走强": "大消费",
    "白酒股集体下跌：贵州茅台盘中跌3.64%": "大消费",
    "贝达药业20CM跌停": "A股医药",
    "创新药概念探底回升：药明康德": "A股医药",
    "港股生物医药股逆势上涨": "A股医药",
    "本周中概财报密集落地": "恒生科技",
    "存储芯片/半导体盘中歇整分化": "恒生科技",
}
def get_track(title):
    for k, v in TRACK_MAP.items():
        if title.startswith(k):
            return v
    return "其他/宽基"

# ---------- 历史事件库统计 ----------
all_events = []
for p in sorted(glob.glob(os.path.join(EVENTS_DIR, 'events-*.json'))):
    if '2026-08-18' in p:
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

from collections import defaultdict
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

# ---------- 追加盘中事件 ----------
new_events = []
for n in news:
    if n['title'][:40] in existing_titles:
        continue
    t = get_track(n['title'])
    st = track_stats.get(t, {})
    seq = len(existing) + len(new_events) + 1
    new_events.append({
        'id': f"N20260818-{seq:03d}",
        'date': '2026-08-18',
        'track': t,
        'category': n.get('category', '行业事件类'),
        'title': n['title'],
        'summary': n.get('summary', ''),
        'source': n.get('source', 'WebSearch'),
        'source_url': n.get('source_url', ''),
        'sentiment': n.get('sentiment', '中性'),
        'score': n.get('score', 50),
        'strength': n.get('score', 50),
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

combined = existing + new_events
with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(combined, f, ensure_ascii=False, indent=1)
print(f"events-2026-08-18.json 共 {len(combined)} 条 (盘前{len(existing)} + 盘中{len(new_events)})")
for e in new_events:
    print(f"  {e['id']} [{e['track']}] {e['sentiment']}{e['score']} | {e['title'][:40]}")

print("\n=== 历史事件 1日收益统计（按赛道） ===")
for t, s in track_stats.items():
    print(f"  {t}: n={s['n']} avg={s['avg_ret_1d']} worst={s['worst_ret_1d']} pos={s['pos_ratio']} ret3d={s['avg_ret_3d']} ret5d={s['avg_ret_5d']}")
