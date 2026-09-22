# -*- coding: utf-8 -*-
"""2026-09-22 盘前档事件库处理：
  ① 回填：9/21 遗留的 8 条「美股标普医药」留空事件（XLV 9/21 收盘已产生 = +0.37%）
  ② 追加本档 42 条盘前事件（window == '盘前(9/21 18:00-9/22 07:30)'，含空集硬守卫）
  ③ 全库完整性扫描
  ④ 1日样本 + 3/5/10日窗口统计 → history/event_stats_20260922.json
⚠️ 口径问题：A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）作代理（§3.90），报告须显式披露。
⚠️ §3.96：回填只对「参考交易日已收盘」的赛道执行；美股标普医药永远比 A股/港股晚 1 个交易日闭环。
"""
import json, os, glob, csv
from collections import defaultdict

BASE = '/Users/jieyang/Documents/WealthHub'
EV = os.path.join(BASE, 'data/processed/events')
HIST = os.path.join(BASE, 'data/processed/history')
TODAY = '2026-09-22'
WIN = '盘前(9/21 18:00-9/22 07:30)'
TRACK_INDEX_REF = {'A股医药': '000933', '大消费': '000932', '恒生科技': 'HSTECH',
                   '美股标普医药': 'XLV', '其他/宽基': '000300'}

# ---------- ① 回填 9/21 美股标普医药 ----------
idx = defaultdict(dict)
with open(os.path.join(HIST, 'indices.csv'), encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        try:
            idx[row['code']][row['date']] = float(row['close'])
        except Exception:
            pass

xlv = idx.get('XLV', {})
xlv_dates = sorted(xlv)
xlv_ret = {}
for i in range(1, len(xlv_dates)):
    d0, d1 = xlv_dates[i - 1], xlv_dates[i]
    xlv_ret[d1] = round((xlv[d1] / xlv[d0] - 1) * 100, 4)
print(f'XLV 序列尾部: ' + ' | '.join(f'{d}:{xlv[d]}' for d in xlv_dates[-4:]))
print(f'XLV 日收益: ' + ' | '.join(f'{d}:{v:+.2f}%' for d, v in sorted(xlv_ret.items())[-4:]))

backfilled, back_detail = 0, []
for f in sorted(glob.glob(os.path.join(EV, 'events-*.json'))):
    ev = json.load(open(f, encoding='utf-8'))
    touched = False
    for e in ev:
        if e['track'] != '美股标普医药':
            continue
        ref = e.setdefault('reference', {})
        if ref.get('actual_ret_1d') is not None:
            continue
        # 参考交易日 = 该事件日期的下一交易日（§3.95）；只在已收盘时回填
        r = xlv_ret.get('2026-09-21') if e['date'] <= '2026-09-21' else None
        if r is None:
            continue
        ref['actual_ret_1d'] = r
        ref['actual_date'] = '2026-09-21'
        ref['ret_1d_ref'] = f'9/21 收盘：XLV 169.01 {r:+.2f}%'
        backfilled += 1
        touched = True
        back_detail.append((e['id'], e['date'], r))
    if touched:
        json.dump(ev, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'\n回填 {backfilled} 条（9/21 遗留美股标普医药）: {back_detail}')

# ---------- ② 追加本档事件 ----------
news = json.load(open(os.path.join(BASE, f'data/processed/news/news-{TODAY}.json'), encoding='utf-8'))
sent = json.load(open(os.path.join(BASE, f'data/processed/news/sentiment-{TODAY}.json'), encoding='utf-8'))
ev_path = os.path.join(EV, f'events-{TODAY}.json')
ev = json.load(open(ev_path, encoding='utf-8')) if os.path.exists(ev_path) else []
existing = {e['title'][:60] for e in ev}

win_sent = [x for x in sent['items'] if x.get('window') == WIN]
if not win_sent:
    raise SystemExit('⚠️ 盘前窗口 sentiment 为 0 条 → per-item `window` 字段可能缺失（§3.88），终止以免静默跳过入库')
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
        'reference': {'ret_3d': None, 'ret_5d': None, 'ret_10d': None,
                      'max_vol': {'低': 1.5, '中': 4.8, '高': 9.0}.get(n.get('volatility'), 4.8),
                      'confidence': n.get('confidence')},
    })
ev.extend(added)
json.dump(ev, open(ev_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'事件库 {TODAY} +{len(added)} 条 → 当日 {len(ev)} 条')

# ---------- ③ 完整性扫描 ----------
files = sorted(glob.glob(os.path.join(EV, 'events-*.json')))
all_ev, dup = [], {}
for f in files:
    for e in json.load(open(f, encoding='utf-8')):
        all_ev.append(e)
        dup[e['title'][:60]] = dup.get(e['title'][:60], 0) + 1
n_blank = sum(1 for e in all_ev if e.get('reference', {}).get('actual_ret_1d') is None)
blank_by_date, blank_by_track = defaultdict(int), defaultdict(int)
for e in all_ev:
    if e.get('reference', {}).get('actual_ret_1d') is None:
        blank_by_date[e['date']] += 1
        blank_by_track[e['track']] += 1
print(f'\n全库 {len(all_ev)} 条 / {len(files)} 日；留空 {n_blank} 条')
print(f'  留空按日: {dict(blank_by_date)}')
print(f'  留空按赛道: {dict(blank_by_track)}')
print(f'  跨日重复标题 {sum(1 for v in dup.values() if v > 1)} 组')

# ---------- ④ 统计 ----------
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


win, ones = defaultdict(lambda: defaultdict(list)), defaultdict(list)
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
    line = (f"  {t:8s} n={len(vs):>4d} 均值={sum(vs)/len(vs):+.2f}% "
            f"上涨占比={sum(1 for v in vs if v>0)/len(vs):.2f}")
    if sp:
        line += f" 强正面={sum(sp)/len(sp):+.2f}%(n={len(sp)})"
    if sn:
        line += f" 强负面={sum(sn)/len(sn):+.2f}%(n={len(sn)})"
    print(line)

print('\n3/5/10 日窗口:')
for t, d in sorted(win.items()):
    row = []
    for n in (3, 5, 10):
        a = d[n]
        row.append(f"{n}日={sum(a)/len(a):+.2f}%(n={len(a)})" if a else f"{n}日=n/a")
    print(f"  {t:8s} " + ' | '.join(row))

# 方向验证：W39（9/21-9/22，本档含 9/21 已回填样本）
w39, hit, tot = defaultdict(lambda: [0, 0]), 0, 0
for e in all_ev:
    v, d = e.get('reference', {}).get('actual_ret_1d'), e.get('direction')
    if e['date'] < '2026-09-21' or e['date'] > '2026-09-21':
        continue
    if v is None or d not in ('利多', '利空'):
        continue
    tot += 1
    ok = (v > 0) if d == '利多' else (v < 0)
    hit += ok
    w39[d][0] += ok
    w39[d][1] += 1
print(f"\n方向验证（9/21 单日）: {hit}/{tot}（{hit/tot*100:.1f}%）"
      + (f" — 利多 {w39['利多'][0]}/{w39['利多'][1]}、利空 {w39['利空'][0]}/{w39['利空'][1]}" if tot else ""))

out = {
    'date': TODAY, 'window': 'preopen', 'total_events': len(all_ev),
    'today_events': len(ev), 'blank': n_blank,
    'blank_by_date': dict(blank_by_date), 'blank_by_track': dict(blank_by_track),
    'backfilled': backfilled, 'backfill_detail': back_detail,
    'onesample': {t: {'n': len(a), 'mean': round(sum(x[0] for x in a) / len(a), 4),
                      'min': min(x[0] for x in a), 'max': max(x[0] for x in a),
                      'up_ratio': round(sum(1 for x in a if x[0] > 0) / len(a), 4)}
                  for t, a in ones.items()},
    'windows': {t: {str(n): ({'n': len(a), 'mean': round(sum(a) / len(a), 4)} if a else {'n': 0, 'mean': None})
                    for n, a in d.items()}
                for t, d in win.items()},
    'direction_check_0921': {'hit': hit, 'total': tot,
                             'by_dir': {k: {'hit': v[0], 'total': v[1]} for k, v in w39.items()}},
    'track_index_map': track_index,
    'note': 'A股医药 3/5/10 日窗口序列实际使用 399006（创业板指）代理（§3.90）；本档回填 9/21 遗留 8 条美股标普医药（XLV 9/21 +0.37%）；本档 42 条参考交易日=9/22（尚未收盘）→ 留空待 9/22 盘后档',
}
json.dump(out, open(os.path.join(HIST, f'event_stats_{TODAY.replace("-", "")}.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print(f'\nSAVED event_stats_{TODAY.replace("-", "")}.json')
