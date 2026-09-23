# -*- coding: utf-8 -*-
"""2026-09-23 盘中档事件库处理：
  ① 追加本档 31 条盘中事件（window == '盘中(07:30-13:30)'，含空集硬守卫）
  ② 全库完整性扫描（留空按 日期×赛道 二维统计，§3.98）
  ③ 历史相似事件匹配（品类 + 赛道 + 关键词 Jaccard → Top3，统计 3/5/10 日涨跌与波动）
  ④ 事件库 3/5/10 日窗口统计 → history/event_stats_intraday_20260923.json
⚠️ 本档不执行回填：A股/港股 9/22 尚未收盘，9/22 盘前 42 条留空事件参考交易日 = 9/22（盘后档闭环）
⚠️ 口径：A股医药 3/5/10 日窗口序列以 399006（创业板指）为代理（§3.90），报告须披露。
"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-23'
WIN = '盘中(07:30-13:30)'

idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass

news = json.load(open(os.path.join(BASE, f'data/processed/news/news-{TODAY}.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
win_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not win_sent:
    raise SystemExit('⚠️ 盘中窗口 sentiment 为 0 条 → per-item `window` 缺失，终止以免静默跳过入库')
print(f'盘中窗口情绪条目 {len(win_sent)}')

# ---------- ① 追加 ----------
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8')) if os.path.exists(ev_path) else []
existing = {e['title'][:60] for e in ev}
added = []
for x in win_sent:
    n = next((y for y in news if y['title'][:60] == x['title']), None)
    if n is None or n['title'][:60] in existing:
        continue
    seq = len(ev) + len(added) + 1
    added.append({
        'id': f"N{TODAY.replace('-', '')}-{seq:03d}", 'date': TODAY, 'track': n['track'],
        'category': n.get('category', '行业事件类'), 'title': n['title'],
        'summary': n.get('summary', ''), 'source': n.get('source', 'WebSearch'),
        'source_url': n.get('source_url', ''), 'sentiment': n.get('sentiment'),
        'score': n.get('score'), 'strength': n.get('strength'),
        'direction': n.get('direction'), 'volatility': n.get('volatility'),
        'reason': n.get('brief', ''),
        'window': WIN,
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'max_vol': {'低': 1.5, '中': 4.8, '高': 9.0}.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence'), 'actual_ret_1d': None, 'actual_date': None},
    })
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'事件库 {TODAY} +{len(added)} 条 → 当日 {len(ev)} 条')

# ---------- ② 完整性扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev = []
for f in files:
    all_ev.extend(json.load(open(f, encoding='utf-8')))
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
bdate, btrack = defaultdict(int), defaultdict(int)
for e in all_ev:
    if e.get('reference', {}).get('actual_ret_1d') is None:
        bdate[e['date']] += 1
        btrack[e['track']] += 1
print(f'全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条')
print(f'  留空按日: {dict(sorted(bdate.items()))}')
print(f'  留空按赛道: {dict(btrack)}')

# ---------- ③ 历史相似事件匹配 ----------
track_index = {'A股医药': '000933', '大消费': '000932', '恒生科技': 'HSTECH',
               '美股标普医药': 'XLV', '其他/宽基': '000300'}
STOP = set('的了和与在是以为对及等这那日前月年。，、；：（）%＋-')


def kw(s):
    return {w for w in __import__('re').findall(r'[\u4e00-\u9fa5]{2,4}', s or '') if w not in STOP}


def fwd(code, d0, n):
    ser = idx.get(code)
    if not ser:
        return None
    ds = sorted(d for d in ser if d >= d0)
    if len(ds) < n + 1:
        return None
    try:
        return round((ser[ds[n]] / ser[ds[0]] - 1) * 100, 4)
    except Exception:
        return None


hist = [e for e in all_ev if e['date'] < TODAY]
sim_out = []
for e in added:
    k0 = kw(e['title'] + e.get('summary', ''))
    cands = []
    for h in hist:
        s = 0.0
        if h['track'] == e['track']:
            s += 55
        if h.get('category') == e.get('category'):
            s += 20
        k1 = kw(h['title'] + h.get('summary', ''))
        if k0 and k1:
            s += 25 * len(k0 & k1) / max(len(k0 | k1), 1)
        if h.get('direction') == e.get('direction'):
            s += 5
        cands.append((round(min(s, 100), 1), h))
    cands.sort(key=lambda x: -x[0])
    top = cands[:3]
    rows = []
    for sc, h in top:
        r3, r5, r10 = (fwd(track_index.get(e['track']), h['date'], n) for n in (3, 5, 10))
        rows.append({'similarity': sc, 'hist_date': h['date'], 'hist_title': h['title'][:44],
                     'hist_direction': h.get('direction'), 'ret_3d': r3, 'ret_5d': r5, 'ret_10d': r10})
    def avg(k):
        v = [r[k] for r in rows if r[k] is not None]
        return round(sum(v) / len(v), 2) if v else None
    sim_out.append({'id': e['id'], 'track': e['track'], 'category': e['category'],
                    'title': e['title'][:50], 'direction': e['direction'], 'strength': e['strength'],
                    'top3': rows, 'avg_3d': avg('ret_3d'), 'avg_5d': avg('ret_5d'), 'avg_10d': avg('ret_10d'),
                    'confidence': int(round(sum(r['similarity'] for r in rows) / max(len(rows), 1)))})

print('\n=== 历史相似事件匹配（Top3，按赛道聚合） ===')
agg = defaultdict(list)
for s in sim_out:
    agg[s['track']].append(s)
for t, arr in sorted(agg.items()):
    a3 = [x['avg_3d'] for x in arr if x['avg_3d'] is not None]
    a5 = [x['avg_5d'] for x in arr if x['avg_5d'] is not None]
    a10 = [x['avg_10d'] for x in arr if x['avg_10d'] is not None]
    cf = [x['confidence'] for x in arr]
    print(f"  {t:10s} n={len(arr):>2d}  3日均值={sum(a3)/len(a3) if a3 else float('nan'):+.2f}%  "
          f"5日={sum(a5)/len(a5) if a5 else float('nan'):+.2f}%  10日={sum(a10)/len(a10) if a10 else float('nan'):+.2f}%  "
          f"平均置信度={sum(cf)/len(cf):.0f}")

print('\n=== 逐条（高相似度样本） ===')
for s in sorted(sim_out, key=lambda x: -max((r['similarity'] for r in x['top3']), default=0)):
    mx = max((r['similarity'] for r in s['top3']), default=0)
    print(f"  [{s['id']}] {s['track']:8s} {s['direction']} {s['strength']:>3d} 最高相似 {mx:>5.1f}  "
          f"3/5/10日 {s['avg_3d']}/{s['avg_5d']}/{s['avg_10d']}  | {s['title'][:34]}")

# ---------- ④ 事件库窗口统计 ----------
win_d = defaultdict(lambda: defaultdict(list))
for e in all_ev:
    code = track_index.get(e['track'])
    if not code:
        continue
    for n in (3, 5, 10):
        x = fwd(code, e['date'], n)
        if x is not None:
            win_d[e['track']][n].append(x)
ones = defaultdict(list)
for e in all_ev:
    v = e.get('reference', {}).get('actual_ret_1d')
    if v is not None and e['track'] in track_index:
        ones[e['track']].append((v, e.get('direction'), e.get('strength')))
print('\n1 日样本（全库，按赛道）:')
for t, arr in sorted(ones.items()):
    vs = [a[0] for a in arr]
    sp = [a[0] for a in arr if a[1] == '利多' and (a[2] or 0) >= 70]
    sn = [a[0] for a in arr if a[1] == '利空' and (a[2] or 0) >= 70]
    line = f"  {t:8s} n={len(vs):>4d} 均值={sum(vs)/len(vs):+.2f}% 上涨占比={sum(1 for v in vs if v>0)/len(vs):.2f}"
    if sp: line += f" 强正面={sum(sp)/len(sp):+.2f}%(n={len(sp)})"
    if sn: line += f" 强负面={sum(sn)/len(sn):+.2f}%(n={len(sn)})"
    print(line)

out = {'date': TODAY, 'window': 'intraday', 'total_events': len(all_ev), 'today_events': len(ev),
       'added': len(added), 'blank': n_blank,
       'blank_by_date': dict(sorted(bdate.items())), 'blank_by_track': dict(btrack),
       'similarity_by_track': {t: {'n': len(arr),
                                   'avg_3d': round(sum(x['avg_3d'] for x in arr if x['avg_3d'] is not None) / max(len([x for x in arr if x['avg_3d'] is not None]), 1), 2),
                                   'avg_5d': round(sum(x['avg_5d'] for x in arr if x['avg_5d'] is not None) / max(len([x for x in arr if x['avg_5d'] is not None]), 1), 2),
                                   'avg_10d': round(sum(x['avg_10d'] for x in arr if x['avg_10d'] is not None) / max(len([x for x in arr if x['avg_10d'] is not None]), 1), 2),
                                   'avg_conf': round(sum(x['confidence'] for x in arr) / len(arr), 1)}
                               for t, arr in agg.items()},
       'similarity_detail': sim_out,
       'onesample': {t: {'n': len(a), 'mean': round(sum(x[0] for x in a) / len(a), 4),
                         'up_ratio': round(sum(1 for x in a if x[0] > 0) / len(a), 4)} for t, a in ones.items()},
       'windows': {t: {str(n): ({'n': len(a), 'mean': round(sum(a) / len(a), 4)} if a else {'n': 0, 'mean': None})
                       for n, a in d.items()} for t, d in win_d.items()},
       'track_index_map': track_index,
       'note': '本档不回填（A股/港股 9/22 未收盘）；A股医药 3/5/10 日窗口以 399006 创业板指为代理（§3.90）'}
json.dump(out, open(os.path.join(HIST, f'event_stats_intraday_20260923.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n已保存 event_stats_intraday_20260923.json')
