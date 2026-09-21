# -*- coding: utf-8 -*-
"""2026-09-21 盘前档事件库处理：
  ① 追加盘前 35 条事件（过滤 window == '盘前(9/20 18:00-9/21 07:30)'，含 §3.88 空集硬守卫）
  ② 回填：本档无可回填项（9/20 周日档 24 条 + 本档 35 条的参考交易日均 = 9/21，须待 9/21 收盘）
  ③ 全库完整性扫描
  ④ 1日样本 + 3/5/10日窗口统计 → history/event_stats_20260921.json
⚠️ 已知口径问题：A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）作代理（§3.90），报告须显式披露。
"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-21'
WIN = '盘前(9/20 18:00-9/21 07:30)'

# ---------- ① 追加盘前事件 ----------
news = json.load(open(os.path.join(BASE, f'data/processed/news/news-{TODAY}.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8')) if os.path.exists(ev_path) else []
existing = {e['title'] for e in ev}

win_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not win_sent:
    raise SystemExit('⚠️ 盘前窗口 sentiment 为 0 条 → per-item `window` 字段可能缺失（§3.88），终止以免静默跳过事件入库')
added = []
for x in win_sent:
    n = next((y for y in news if y['title'][:60] == x['title']), None)
    if n is None or n['title'] in existing:
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
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'max_vol': {'低': 1.5, '中': 4.8, '高': 9.0}.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence')},
    })
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'事件库 {TODAY} +{len(added)} 条 → 当日 {len(ev)} 条')

# ---------- ② 回填检查 ----------
# 参考交易日 = 9/21（尚未收盘）→ 本档不可回填；仅扫描全库留空分布
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev, dup = [], {}
for f in files:
    for e in json.load(open(f, encoding='utf-8')):
        all_ev.append(e)
        dup[e['title'][:60]] = dup.get(e['title'][:60], 0) + 1
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
blank_by_date = defaultdict(int)
for e in all_ev:
    if e.get('reference', {}).get('actual_ret_1d') is None:
        blank_by_date[e['date']] += 1
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条 {dict(blank_by_date)}；跨日重复标题 {sum(1 for v in dup.values() if v > 1)} 组')

# ---------- ③ 统计 ----------
idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass
track_index = {'A股医药': '399006', '大消费': '000932', '恒生科技': 'HSTECH',
               '美股标普医药': 'XLV', '其他/宽基': '000300'}


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


win = defaultdict(lambda: defaultdict(list))
ones = defaultdict(list)
for e in all_ev:
    t = e['track']
    r = e.get('reference', {})
    v = r.get('actual_ret_1d')
    if v is not None and t in track_index:
        ones[t].append((v, e.get('direction'), e.get('strength')))
    code = track_index.get(t)
    if not code:
        continue
    for n in (3, 5, 10):
        x = fwd(code, e['date'], n)
        if x is not None:
            win[t][n].append(x)

print('\n1 日样本（按赛道，全库）:')
for t, arr in sorted(ones.items()):
    vs = [a[0] for a in arr]
    sp = [a[0] for a in arr if a[1] == '利多' and (a[2] or 0) >= 70]
    sn = [a[0] for a in arr if a[1] == '利空' and (a[2] or 0) >= 70]
    print(f"  {t:8s} n={len(vs):>4d} 均值={sum(vs)/len(vs):+.2f}% 上涨占比={sum(1 for v in vs if v>0)/len(vs):.2f} "
          f"强正面={sum(sp)/len(sp):+.2f}%(n={len(sp)}) 强负面={sum(sn)/len(sn):+.2f}%(n={len(sn)})")

print('\n3/5/10 日窗口:')
for t, d in sorted(win.items()):
    row = []
    for n in (3, 5, 10):
        a = d[n]
        row.append(f"{n}日={sum(a)/len(a):+.2f}%(n={len(a)})" if a else f"{n}日=n/a")
    print(f"  {t:8s} " + ' | '.join(row))

# 方向验证（W38 聚合，作为参考）
w38, hit, tot = defaultdict(lambda: [0, 0]), 0, 0
for e in all_ev:
    v, d = e.get('reference', {}).get('actual_ret_1d'), e.get('direction')
    if e['date'] < '2026-09-14' or e['date'] > '2026-09-18':
        continue
    if v is None or d not in ('利多', '利空'):
        continue
    tot += 1
    ok = (v > 0) if d == '利多' else (v < 0)
    hit += ok
    w38[d][0] += ok
    w38[d][1] += 1
print(f"\n方向验证（W38 聚合）: {hit}/{tot}（{hit/tot*100:.1f}%）"
      + (f" — 利多 {w38['利多'][0]}/{w38['利多'][1]}、利空 {w38['利空'][0]}/{w38['利空'][1]}" if tot else ""))

out = {
    'date': TODAY, 'window': 'preopen', 'total_events': len(all_ev),
    'today_events': len(ev), 'blank': n_blank, 'blank_by_date': dict(blank_by_date),
    'onesample': {t: {'n': len(a), 'mean': round(sum(x[0] for x in a) / len(a), 4),
                      'min': min(x[0] for x in a), 'max': max(x[0] for x in a),
                      'up_ratio': round(sum(1 for x in a if x[0] > 0) / len(a), 4)}
                  for t, a in ones.items()},
    'windows': {t: {str(n): ({'n': len(a), 'mean': round(sum(a) / len(a), 4)} if a else {'n': 0, 'mean': None})
                     for n, a in d.items()}
                for t, d in win.items()},
    'direction_check_w38': {'hit': hit, 'total': tot,
                            'by_dir': {k: {'hit': v[0], 'total': v[1]} for k, v in w38.items()}},
    'track_index_map': track_index,
    'note': 'A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）代理（§3.90）；本档无可回填项（9/20+9/21 事件参考交易日均=9/21）',
}
json.dump(out, open(os.path.join(HIST, 'event_stats_20260921.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\nSAVED event_stats_20260921.json')
