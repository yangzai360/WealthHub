# -*- coding: utf-8 -*-
"""2026-09-04 盘后: 事件库追加盘后8条(24-31) + 全量回填当日 actual_ret_1d + 统计"""
import json, os, glob
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EVENTS_DIR = os.path.join(BASE, 'data/processed/events')
SENT_FILE = os.path.join(BASE, 'data/processed/news/sentiment-2026-09-04.json')
EV_FILE = os.path.join(EVENTS_DIR, 'events-2026-09-04.json')

with open(SENT_FILE, encoding='utf-8') as f:
    sent = json.load(f)
with open(EV_FILE, encoding='utf-8') as f:
    events = json.load(f)

# ---------- 1. 追加盘后事件 (sentiment 中未入库的) ----------
existing_titles = set(e['title'][:40] for e in events)

# 历史统计(排除今日)供 reference 填充
all_events = []
for p in sorted(glob.glob(os.path.join(EVENTS_DIR, 'events-*.json'))):
    if '2026-09-04' in p:
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

stats = defaultdict(lambda: {'n': 0, 'rets': [], 'ret3': [], 'ret5': [], 'ret10': []})
for e in all_events:
    t = e.get('track', '?')
    s = stats[t]
    r1 = get_ret1d(e)
    if r1 is not None:
        s['n'] += 1
        s['rets'].append(float(r1))
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
        'pos_ratio': round(sum(1 for r in s['rets'] if r > 0)/s['n'], 2) if s['n'] else None,
        'avg_ret_3d': round(sum(s['ret3'])/len(s['ret3']), 2) if s['ret3'] else None,
        'avg_ret_5d': round(sum(s['ret5'])/len(s['ret5']), 2) if s['ret5'] else None,
        'avg_ret_10d': round(sum(s['ret10'])/len(s['ret10']), 2) if s['ret10'] else None,
        'max_vol': round(max([abs(r) for r in s['rets']])*2, 2) if s['rets'] else None,
    }

new_events = []
for n in sent:
    if n['title'][:40] in existing_titles:
        continue
    t = n.get('track', '其他/宽基')
    st = track_stats.get(t, {})
    seq = len(events) + len(new_events) + 1
    new_events.append({
        'id': f"N20260904-{seq:03d}",
        'date': '2026-09-04',
        'track': t,
        'category': '行业事件类',
        'title': n['title'],
        'summary': n.get('comment', ''),
        'source': 'WebSearch',
        'source_url': '',
        'sentiment': n.get('sentiment', '中性'),
        'score': n.get('score', 50),
        'strength': n.get('strength', 50),
        'direction': n.get('direction', '中性'),
        'volatility': n.get('volatility', '中'),
        'reason': n.get('comment', ''),
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

combined = events + new_events
print(f'追加盘后事件 {len(new_events)} 条 → events 共 {len(combined)} 条')

# ---------- 2. 回填当日 actual_ret_1d ----------
# 赛道口径 (9/4 收盘): A股医药 ETF均值 / 大消费 中证消费 / 恒生科技 HSTECH / 宏观 沪指 / 其他宽基 个股均值
RET_MAP = {
    'A股医药': -0.08,      # (医疗ETF 0.00 + 医药ETF广发 -0.16)/2
    '大消费': 2.65,        # 中证消费 +2.65%
    '恒生科技': 2.27,      # HSTECH +2.27%
    '宏观': -0.30,         # 沪指 -0.30%
    '其他/宽基': 2.00,     # (广联达 +3.02 + 通威 +0.98)/2
}
backfilled, pending = 0, 0
for e in combined:
    if e['date'] != '2026-09-04':
        continue
    cur = e.get('reference', {}).get('actual_ret_1d')
    if cur is not None:
        continue
    t = e['track']
    if t == '美股标普医药':
        pending += 1  # 待 9/7 用 XLV 9/4 收盘回填
        continue
    ret = RET_MAP.get(t)
    if ret is None:
        pending += 1
        continue
    if 'reference' not in e:
        e['reference'] = {}
    e['reference']['actual_ret_1d'] = ret
    e['reference']['actual_date'] = '2026-09-04'
    backfilled += 1
print(f'回填 {backfilled} 条 / 待后续 {pending} 条(美股标普医药等)')

with open(EV_FILE, 'w', encoding='utf-8') as f:
    json.dump(combined, f, ensure_ascii=False, indent=1)
print('已写 events-2026-09-04.json')

# ---------- 3. 统计(全库含今日) ----------
all_events2 = []
for p in sorted(glob.glob(os.path.join(EVENTS_DIR, 'events-*.json'))):
    with open(p, encoding='utf-8') as f:
        all_events2.extend(json.load(f))

def ret1(e):
    v = e.get('actual_ret_1d')
    if v is None:
        v = e.get('reference', {}).get('actual_ret_1d')
    return v

# 全局 1 日样本统计
n_total = sum(1 for e in all_events2 if ret1(e) is not None)
print(f'\n事件库总计 {len(all_events2)} 条, 1日样本 {n_total} 条')

# 方向验证 (sentiment 口径): 需要 全部日期 sentiment
sent_stats = {'total': 0, 'ok': 0}
sent_by_date = defaultdict(list)
for d in sorted(glob.glob(os.path.join(BASE, 'data/processed/news', 'sentiment-*.json'))):
    if '2026-09-04' in d:
        continue
    with open(d, encoding='utf-8') as f:
        for x in json.load(f):
            sent_by_date[x['date']].append(x)

# 用事件库 actual_ret_1d 对照事件 sentiment 方向(事件 id 日期回填)
def direction_ok(sent_dir, ret):
    if sent_dir == '利多':
        return ret > 0
    if sent_dir == '利空':
        return ret < 0
    return None  # 中性不计入

ok = total = 0
by_track = defaultdict(lambda: [0, 0])
# 遍历所有有实际收益的事件(actual_date 存在)
for e in all_events2:
    ar = ret1(e)
    if ar is None:
        continue
    sd = e.get('direction')
    if sd not in ('利多', '利空'):
        continue
    total += 1
    r = float(ar)
    if (sd == '利多' and r > 0) or (sd == '利空' and r < 0):
        ok += 1
        by_track[e['track']][0] += 1
    by_track[e['track']][1] += 1

print(f'方向验证(事件库口径, 中性不计): 全局 {ok}/{total} ({round(ok/total*100) if total else 0}%)')
for t, (o, n) in sorted(by_track.items(), key=lambda x: -x[1][1]):
    if n:
        print(f'  {t}: {o}/{n} ({round(o/n*100)}%)')

# 3/5/10 日窗口
for k, label in [('ret_3d', '3日'), ('ret_5d', '5日'), ('ret_10d', '10日')]:
    by = defaultdict(list)
    for e in all_events2:
        v = e.get('reference', {}).get(k)
        if v is not None:
            by[e['track']].append(float(v))
    parts = []
    for t, arr in by.items():
        if arr:
            parts.append(f"{t}: {sum(arr)/len(arr):+.2f}% (n={len(arr)})")
    print(f'{label}窗口: ' + ' / '.join(parts))

# 保存统计
out_stats = {
    'date': '2026-09-04',
    'total_events': len(all_events2),
    'sample_1d': n_total,
    'direction_ok': ok,
    'direction_total': total,
    'direction_rate': round(ok/total, 3) if total else None,
    'track_ok': {t: {'ok': v[0], 'total': v[1]} for t, v in by_track.items()},
    'ret_map': RET_MAP,
}
with open(os.path.join(EVENTS_DIR, 'event_stats_20260904.json'), 'w', encoding='utf-8') as f:
    json.dump(out_stats, f, ensure_ascii=False, indent=1)
print('\n已写 event_stats_20260904.json')
